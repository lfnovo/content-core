"""Video processing with vision model analysis of extracted frames."""
import asyncio
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from content_core.common import ProcessSourceState
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
    """
    Calculate optimal fps and max_frames based on video duration.

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
    """
    Extract frames from video at specified FPS using ffmpeg.

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
                prompt=f"Describe what you see in this video frame at timestamp {ts_str}. Be concise but thorough.",
            )

            response = await model.achat_complete([message])
            description = response.choices[0].message.content or ""
            return (timestamp, description)

        except Exception as e:
            logger.warning(f"Frame analysis failed at {timestamp}s: {e}")
            return (timestamp, f"[Frame analysis failed: {e}]")


async def extract_video_with_vision(data: ProcessSourceState) -> Dict[str, Any]:
    """
    Process a video file using vision model for frame analysis and audio transcription.

    Pipeline:
    1. Get duration and calculate frame sampling params
    2. Extract frames with ffmpeg
    3. Analyze frames in parallel with vision model (semaphore-controlled)
    4. Extract best audio stream and transcribe (non-fatal if it fails)
    5. Return combined visual analysis + audio transcript

    Args:
        data: ProcessSourceState with file_path, vision config, and optional audio config.

    Returns:
        Dict with combined visual analysis and audio transcript content and metadata.
    """
    file_path = data.file_path
    assert file_path, "No file path provided"

    title = os.path.basename(file_path)
    temp_dirs = []

    try:
        from esperanto import AIFactory

        # Get video duration
        duration = await get_video_duration(file_path)
        logger.info(f"Video duration: {duration:.1f}s")

        # Calculate frame extraction parameters
        fps, max_frames = calculate_frame_params(duration)
        logger.info(f"Using fps={fps}, max_frames={max_frames}")

        # Extract frames
        frames_dir = tempfile.mkdtemp(prefix="video_frames_")
        temp_dirs.append(frames_dir)
        frames = await extract_frames(file_path, fps, max_frames, frames_dir)

        if not frames:
            logger.warning("No frames extracted from video")
            return {
                "content": f"[Video: {title} - no frames could be extracted]",
                "title": title,
            }

        # Create vision model
        model = AIFactory.create_language(
            data.vision_provider, data.vision_model, config=data.vision_config
        )

        # Analyze frames in parallel with semaphore
        semaphore = asyncio.Semaphore(5)
        tasks = [
            _analyze_frame(frame_path, timestamp, model, semaphore)
            for frame_path, timestamp in frames
        ]
        frame_descriptions = await asyncio.gather(*tasks)

        # Build visual content section
        visual_lines = ["## Visual Content\n"]
        for timestamp, desc in sorted(frame_descriptions, key=lambda x: x[0]):
            ts_str = format_timestamp(timestamp)
            visual_lines.append(f"**[{ts_str}]** {desc}\n")

        visual_content = "\n".join(visual_lines)

        # === Audio extraction + transcription (non-fatal) ===
        audio_content = ""
        try:
            from content_core.processors.video import (
                get_audio_streams,
                select_best_audio_stream,
                extract_audio_from_video,
            )

            streams = await get_audio_streams(file_path)
            if streams:
                best_stream = await select_best_audio_stream(streams)
                if best_stream:
                    stream_index = streams.index(best_stream)
                    audio_file = os.path.splitext(file_path)[0] + "_audio.mp3"
                    try:
                        await extract_audio_from_video(
                            file_path, audio_file, stream_index
                        )

                        # Split into ~1 min segments with timestamp tracking
                        from moviepy import AudioFileClip
                        from content_core.processors.audio import (
                            extract_audio,
                            transcribe_audio_segment,
                        )
                        from content_core.config import get_audio_concurrency

                        audio_clip = AudioFileClip(audio_file)
                        audio_duration = audio_clip.duration
                        audio_clip.close()

                        segment_length = 60  # 1 minute
                        segments = []  # (segment_file, start_time)

                        with tempfile.TemporaryDirectory() as audio_temp:
                            if audio_duration > segment_length:
                                for i in range(math.ceil(audio_duration / segment_length)):
                                    start = i * segment_length
                                    end = min((i + 1) * segment_length, audio_duration)
                                    seg_file = os.path.join(audio_temp, f"seg_{i:03d}.mp3")
                                    extract_audio(audio_file, seg_file, start, end)
                                    segments.append((seg_file, start))
                            else:
                                segments.append((audio_file, 0.0))

                            # Create STT model
                            from content_core.models import ModelFactory
                            from content_core.config import CONFIG

                            stt_model = None
                            if data.audio_provider and data.audio_model:
                                try:
                                    timeout = CONFIG.get('speech_to_text', {}).get('timeout', 3600)
                                    stt_config = {'timeout': timeout} if timeout else {}
                                    if data.audio_config:
                                        stt_config.update(data.audio_config)
                                    if 'endpoint_stt' in stt_config and 'base_url' not in stt_config:
                                        stt_config['base_url'] = stt_config.pop('endpoint_stt')
                                    stt_model = AIFactory.create_speech_to_text(
                                        data.audio_provider, data.audio_model, stt_config
                                    )
                                except Exception as e:
                                    logger.warning(f"Custom STT model failed: {e}, using default")
                            if stt_model is None:
                                stt_model = ModelFactory.get_model("speech_to_text")

                            # Transcribe segments with timestamps
                            concurrency = get_audio_concurrency()
                            sem = asyncio.Semaphore(concurrency)
                            tasks = [
                                transcribe_audio_segment(seg_file, stt_model, sem)
                                for seg_file, _ in segments
                            ]
                            transcriptions = await asyncio.gather(*tasks)

                            # Format with timestamps
                            parts = []
                            for (_, start_time), text in zip(segments, transcriptions):
                                ts = format_timestamp(start_time)
                                parts.append(f"**[{ts}]** {text}")
                            audio_content = "\n\n".join(parts)
                    except Exception as e:
                        logger.warning(f"Audio transcription failed: {e}")
                    finally:
                        if os.path.exists(audio_file):
                            os.unlink(audio_file)
            else:
                logger.info("No audio streams found in video")
        except Exception as e:
            logger.warning(f"Audio extraction from video failed: {e}")

        # Combine visual analysis and audio transcript
        content_parts = [f"# Video Analysis: {title}\n"]
        content_parts.append(visual_content)
        if audio_content:
            content_parts.append("\n## Audio Transcript\n")
            content_parts.append(audio_content)

        metadata = {
            "video_duration": duration,
            "frames_analyzed": len(frames),
            "visual_analysis": visual_content,
        }
        if audio_content:
            metadata["audio_transcript"] = audio_content

        return {
            "content": "\n".join(content_parts),
            "title": title,
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"Video vision processing failed: {e}")
        return {
            "content": f"[Video: {title} - vision processing failed: {e}]",
            "title": title,
        }

    finally:
        cleanup_temp_files(temp_dirs)
