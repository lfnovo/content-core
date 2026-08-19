"""Video processing with vision model analysis of extracted frames."""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from content_core.common.state import ExtractionOutput
from content_core.config import ContentCoreConfig
from content_core.logging import logger


async def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")

    return float(stdout.decode().strip())


def calculate_frame_params(duration: float) -> Tuple[float, int]:
    """Calculate optimal fps and max_frames based on video duration.

    | Duration   | Sample Rate | Max Frames |
    |------------|-------------|------------|
    | <= 60s     | 1 fps       | 60         |
    | 61s - 5min | 0.5 fps     | 150        |
    | 5min - 15m | 0.2 fps     | 180        |
    | > 15min    | 0.1 fps     | 180        |
    """
    if duration <= 60:
        return (1.0, 60)
    elif duration <= 300:
        return (0.5, 150)
    elif duration <= 900:
        return (0.2, 180)
    else:
        return (0.1, 180)


async def extract_frames(
    video_path: str,
    fps: float = 1.0,
    max_frames: int = 60,
    output_dir: Optional[str] = None,
) -> List[Tuple[str, float]]:
    """Extract frames from video at specified FPS using ffmpeg.

    Returns:
        List of (frame_path, timestamp_seconds) tuples.
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="video_frames_")

    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"fps={fps}",
        "-frames:v", str(max_frames),
        "-q:v", "2",
        output_pattern,
        "-y",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.warning(f"FFmpeg stderr: {stderr.decode()}")

    frames = []
    for i, frame_file in enumerate(sorted(Path(output_dir).glob("frame_*.jpg"))):
        timestamp = i / fps
        frames.append((str(frame_file), timestamp))
        if len(frames) >= max_frames:
            break

    logger.info(f"Extracted {len(frames)} frames from video at {fps} fps")
    return frames


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def cleanup_temp_files(paths: List[str]) -> None:
    """Remove temporary files and directories."""
    for path in paths:
        if path is None:
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.unlink(path)
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")


async def _analyze_frame(
    frame_path: str,
    timestamp: float,
    model,
    semaphore: asyncio.Semaphore,
) -> Tuple[float, str]:
    """Analyze a single frame with the vision model, controlled by semaphore."""
    async with semaphore:
        try:
            from esperanto.utils.vision import create_image_message

            ts_str = format_timestamp(timestamp)
            message = create_image_message(
                frame_path,
                prompt=(
                    f"Describe what you see in this video frame at timestamp {ts_str}. "
                    "Be concise but thorough."
                ),
            )

            response = await model.achat_complete([message])
            description = response.choices[0].message.content or ""
            return (timestamp, description)

        except Exception as e:
            logger.warning(f"Frame analysis failed at {timestamp}s: {e}")
            return (timestamp, f"[Frame analysis failed: {e}]")


async def _transcribe_video_audio(
    file_path: str, config: ContentCoreConfig
) -> str:
    """Extract audio from a video and transcribe it. Returns "" on failure."""
    from content_core.processors.media.audio import transcribe_audio
    from content_core.processors.media.video import (
        extract_audio_from_video,
        get_audio_streams,
        select_best_audio_stream,
    )

    streams = await get_audio_streams(file_path)
    if not streams:
        logger.info("No audio streams found in video")
        return ""

    best_stream = await select_best_audio_stream(streams)
    if not best_stream:
        return ""

    stream_index = streams.index(best_stream)
    audio_file = os.path.splitext(file_path)[0] + "_audio.mp3"
    try:
        success = await extract_audio_from_video(file_path, audio_file, stream_index)
        if not success:
            return ""
        result = await transcribe_audio(audio_file, config)
        return result.content or ""
    finally:
        if os.path.exists(audio_file):
            try:
                os.unlink(audio_file)
            except OSError:
                pass


async def extract_video_with_vision(
    file_path: str, config: ContentCoreConfig
) -> ExtractionOutput:
    """Process a video file using vision-model frame analysis + audio transcription.

    Pipeline:
      1. Extract frames with ffmpeg (adaptive sampling).
      2. Analyze frames in parallel with vision model.
      3. Extract best audio stream and transcribe via `transcribe_audio` (non-fatal).
      4. Combine visual + audio content.
    """
    title = os.path.basename(file_path)
    temp_dirs: List[str] = []

    try:
        from esperanto import AIFactory

        duration = await get_video_duration(file_path)
        logger.info(f"Video duration: {duration:.1f}s")

        fps, max_frames = calculate_frame_params(duration)
        logger.info(f"Using fps={fps}, max_frames={max_frames}")

        frames_dir = tempfile.mkdtemp(prefix="video_frames_")
        temp_dirs.append(frames_dir)
        frames = await extract_frames(file_path, fps, max_frames, frames_dir)

        if not frames:
            logger.warning("No frames extracted from video")
            return ExtractionOutput(
                content=f"[Video: {title} - no frames could be extracted]",
                title=title,
                source_type="file",
            )

        model = AIFactory.create_language(
            config.vision_provider, config.vision_model, config=config.vision_config
        )

        semaphore = asyncio.Semaphore(5)
        tasks = [
            _analyze_frame(frame_path, timestamp, model, semaphore)
            for frame_path, timestamp in frames
        ]
        frame_descriptions = await asyncio.gather(*tasks)

        visual_lines = ["## Visual Content\n"]
        for timestamp, desc in sorted(frame_descriptions, key=lambda x: x[0]):
            ts_str = format_timestamp(timestamp)
            visual_lines.append(f"**[{ts_str}]** {desc}\n")
        visual_content = "\n".join(visual_lines)

        # Audio extraction + transcription is non-fatal
        audio_content = ""
        try:
            audio_content = await _transcribe_video_audio(file_path, config)
        except Exception as e:
            logger.warning(f"Audio extraction/transcription from video failed: {e}")

        content_parts = [f"# Video Analysis: {title}\n", visual_content]
        if audio_content:
            content_parts.append("\n## Audio Transcript\n")
            content_parts.append(audio_content)

        metadata = {
            "video_duration": duration,
            "frames_analyzed": len(frames),
        }
        if audio_content:
            metadata["audio_transcript"] = audio_content

        return ExtractionOutput(
            content="\n".join(content_parts),
            title=title,
            source_type="file",
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Video vision processing failed: {e}")
        return ExtractionOutput(
            content=f"[Video: {title} - vision processing failed: {e}]",
            title=title,
            source_type="file",
        )

    finally:
        cleanup_temp_files(temp_dirs)
