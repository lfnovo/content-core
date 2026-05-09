import asyncio
import json
import math
import os
import subprocess
import tempfile
import traceback
from functools import partial

from content_core.common.retry import retry_audio_transcription
from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput


async def get_audio_duration(input_file: str) -> float:
    """Get audio duration in seconds using ffprobe."""

    def _probe(path):
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_entries", "format=duration",
            path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    return await asyncio.get_event_loop().run_in_executor(None, partial(_probe, input_file))


def split_audio_segment(
    input_file: str, output_file: str, start_time: float, end_time: float
) -> None:
    """Extract an audio segment using ffmpeg with stream copy (no re-encoding)."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-ss", str(start_time),
        "-to", str(end_time),
        "-codec", "copy",
        "-map_chapters", "-1",
        output_file,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg split failed: {result.stderr}")


async def split_audio(input_file, segment_length_minutes=15, output_prefix=None):
    """Split an audio file into segments asynchronously."""

    def _split(input_file, segment_length_minutes, output_prefix):
        input_file_abs = os.path.abspath(input_file)
        output_dir = os.path.dirname(input_file_abs)
        os.makedirs(output_dir, exist_ok=True)

        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(input_file_abs))[0]

        # Get duration via ffprobe
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_entries", "format=duration",
            input_file_abs,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        duration = float(json.loads(result.stdout)["format"]["duration"])

        segment_length_s = segment_length_minutes * 60
        total_segments = math.ceil(duration / segment_length_s)
        logger.debug(f"Splitting file: {input_file_abs} into {total_segments} segments")

        output_files = []
        for i in range(total_segments):
            start_time = i * segment_length_s
            end_time = min((i + 1) * segment_length_s, duration)
            output_filename = f"{output_prefix}_{str(i + 1).zfill(3)}.mp3"
            output_path = os.path.join(output_dir, output_filename)

            split_audio_segment(input_file_abs, output_path, start_time, end_time)
            output_files.append(output_path)
            logger.debug(
                f"Exported segment {i + 1}/{total_segments}: {output_filename}"
            )

        return output_files

    return await asyncio.get_event_loop().run_in_executor(
        None, partial(_split, input_file, segment_length_minutes, output_prefix)
    )


def extract_audio(
    input_file: str, output_file: str, start_time: float = None, end_time: float = None
) -> None:
    """Extract audio from a file, optionally trimming to a time range.

    Uses ffmpeg with stream copy for fast, lossless extraction.
    """
    cmd = ["ffmpeg", "-y", "-i", input_file]

    if start_time is not None:
        cmd.extend(["-ss", str(start_time)])
    if end_time is not None:
        cmd.extend(["-to", str(end_time)])

    cmd.extend(["-codec", "copy", "-map_chapters", "-1", output_file])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg extract failed: {result.stderr}")


@retry_audio_transcription()
async def _transcribe_segment(audio_file, model):
    """Internal function to transcribe a single segment - wrapped with retry logic."""
    return (await model.atranscribe(audio_file)).text


async def transcribe_audio_segment(audio_file, model, semaphore):
    """Transcribe a single audio segment with concurrency control and retry logic."""
    async with semaphore:
        return await _transcribe_segment(audio_file, model)


async def transcribe_audio(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Transcribe an audio file using STT."""
    from esperanto import AIFactory

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = os.path.splitext(os.path.basename(file_path))[0]

            # Get duration via ffprobe
            duration_s = await get_audio_duration(file_path)
            segment_length_s = 10 * 60
            output_files = []

            if duration_s > segment_length_s:
                logger.info(
                    f"Audio is longer than 10 minutes ({duration_s:.0f}s), splitting into "
                    f"{math.ceil(duration_s / segment_length_s)} segments"
                )
                loop = asyncio.get_event_loop()
                for i in range(math.ceil(duration_s / segment_length_s)):
                    start_time = i * segment_length_s
                    end_time = min((i + 1) * segment_length_s, duration_s)
                    output_filename = f"{output_prefix}_{str(i + 1).zfill(3)}.mp3"
                    output_path = os.path.join(temp_dir, output_filename)
                    await loop.run_in_executor(
                        None, partial(extract_audio, file_path, output_path, start_time, end_time)
                    )
                    output_files.append(output_path)
            else:
                output_files = [file_path]

            # Determine STT model from config
            if config.audio_provider and config.audio_model:
                try:
                    logger.info(
                        f"Using custom audio model: {config.audio_provider}/{config.audio_model}"
                    )
                    stt_config = {"timeout": config.stt_timeout} if config.stt_timeout else {}
                    speech_to_text_model = AIFactory.create_speech_to_text(
                        config.audio_provider, config.audio_model, stt_config
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create custom audio model "
                        f"'{config.audio_provider}/{config.audio_model}': {e}. "
                        f"Falling back to default model."
                    )
                    stt_config = {"timeout": config.stt_timeout} if config.stt_timeout else {}
                    speech_to_text_model = AIFactory.create_speech_to_text(
                        config.stt_provider, config.stt_model, stt_config
                    )
            else:
                stt_config = {"timeout": config.stt_timeout} if config.stt_timeout else {}
                speech_to_text_model = AIFactory.create_speech_to_text(
                    config.stt_provider, config.stt_model, stt_config
                )

            concurrency = config.audio_concurrency
            semaphore = asyncio.Semaphore(concurrency)

            logger.debug(
                f"Transcribing {len(output_files)} audio segments with concurrency limit of {concurrency}"
            )

            transcription_tasks = [
                transcribe_audio_segment(audio_file, speech_to_text_model, semaphore)
                for audio_file in output_files
            ]

            transcriptions = await asyncio.gather(*transcription_tasks)

            return ExtractionOutput(
                content=" ".join(transcriptions),
                source_type="file",
                identified_type="audio/*",
                metadata={"segments_count": len(output_files)},
            )
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        logger.error(traceback.format_exc())
        raise
