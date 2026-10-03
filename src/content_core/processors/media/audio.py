import asyncio
import json
import math
import os
import shutil
import subprocess
import tempfile
import traceback
from functools import partial

from content_core.common.exceptions import (
    ConfigurationError,
    ContentCoreError,
    ExternalServiceError,
    FileOperationError,
)
from content_core.common.retry import retry_audio_transcription
from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput

# STT providers validate uploads by filename extension, not by content. OpenAI
# accepts 'ogg' and 'oga' but rejects 'opus' outright, even though `.opus` *is*
# Opus-in-Ogg and the bytes are identical — verified with the same file under
# both names, holding the multipart Content-Type constant. Present such files
# under an accepted extension; the user's own file is never renamed.
UPLOAD_EXTENSION_ALIASES = {".opus": ".ogg"}


def upload_extension(path: str) -> str:
    """Return the extension a provider will accept for this file."""
    ext = os.path.splitext(path)[1].lower()
    return UPLOAD_EXTENSION_ALIASES.get(ext, ext)


def _aliased_upload_path(file_path: str, temp_dir: str) -> str:
    """Expose `file_path` under a provider-accepted extension, without copying.

    Falls back to a real copy where symlinks are unavailable.
    """
    alias = os.path.join(
        temp_dir, f"{os.path.splitext(os.path.basename(file_path))[0]}{upload_extension(file_path)}"
    )
    source = os.path.abspath(file_path)
    try:
        os.symlink(source, alias)
    except (OSError, NotImplementedError):
        shutil.copy2(source, alias)
    return alias


def run_ffmpeg_tool(cmd: list, what: str) -> subprocess.CompletedProcess:
    """Run an ffmpeg/ffprobe command; any failure raises FileOperationError."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        raise FileOperationError(
            f"{what} could not run (is ffmpeg installed?): {e}"
        ) from e
    if result.returncode != 0:
        raise FileOperationError(f"{what} failed: {result.stderr}")
    return result


def _parse_duration(ffprobe_stdout: str, path: str) -> float:
    try:
        return float(json.loads(ffprobe_stdout)["format"]["duration"])
    except (ValueError, KeyError, TypeError) as e:
        raise FileOperationError(f"ffprobe returned no duration for {path}") from e


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
        result = run_ffmpeg_tool(cmd, "ffprobe")
        return _parse_duration(result.stdout, path)

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
    run_ffmpeg_tool(cmd, "ffmpeg split")


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
        result = run_ffmpeg_tool(cmd, "ffprobe")
        duration = _parse_duration(result.stdout, input_file_abs)

        segment_length_s = segment_length_minutes * 60
        total_segments = math.ceil(duration / segment_length_s)
        logger.debug(f"Splitting file: {input_file_abs} into {total_segments} segments")

        # Segments are stream-copied, so they must keep the source container:
        # muxing e.g. an Opus stream into a .mp3 output makes ffmpeg fail.
        source_ext = os.path.splitext(input_file_abs)[1] or ".mp3"

        output_files = []
        for i in range(total_segments):
            start_time = i * segment_length_s
            end_time = min((i + 1) * segment_length_s, duration)
            output_filename = f"{output_prefix}_{str(i + 1).zfill(3)}{source_ext}"
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

    run_ffmpeg_tool(cmd, "ffmpeg extract")


@retry_audio_transcription()
async def _transcribe_segment(audio_file, model):
    """Internal function to transcribe a single segment - wrapped with retry logic."""
    return (await model.atranscribe(audio_file)).text


async def transcribe_audio_segment(audio_file, model, semaphore):
    """Transcribe a single audio segment with concurrency control and retry logic.

    Raises ExternalServiceError once the provider still fails after retries.
    """
    async with semaphore:
        try:
            return await _transcribe_segment(audio_file, model)
        except ContentCoreError:
            raise
        except Exception as e:
            raise ExternalServiceError(
                f"Speech-to-text failed for {os.path.basename(audio_file)}: {e!r}"
            ) from e


def _create_stt_model(provider: str, model: str, stt_config: dict):
    from esperanto import AIFactory

    try:
        return AIFactory.create_speech_to_text(provider, model, stt_config)
    except Exception as e:
        raise ConfigurationError(
            f"Could not create speech-to-text model '{provider}/{model}': {e}"
        ) from e


async def transcribe_audio(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Transcribe an audio file using STT.

    Raises:
        FileOperationError: ffmpeg/ffprobe could not read or split the file.
        ConfigurationError: the STT model could not be created.
        ExternalServiceError: the STT provider failed after retries.
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = os.path.splitext(os.path.basename(file_path))[0]

            # Get duration via ffprobe
            duration_s = await get_audio_duration(file_path)
            segment_length_s = config.audio_segment_minutes * 60
            output_files = []

            # Segments are stream-copied, so they must keep the source container:
            # muxing e.g. an Opus stream into a .mp3 output makes ffmpeg fail.
            # The alias only renames within the same container (.opus -> .ogg),
            # so stream copy stays valid while the upload becomes acceptable.
            source_ext = upload_extension(file_path) or ".mp3"

            if segment_length_s and duration_s > segment_length_s:
                logger.info(
                    f"Audio is longer than {config.audio_segment_minutes} minutes "
                    f"({duration_s:.0f}s), splitting into "
                    f"{math.ceil(duration_s / segment_length_s)} segments"
                )
                loop = asyncio.get_event_loop()
                for i in range(math.ceil(duration_s / segment_length_s)):
                    start_time = i * segment_length_s
                    end_time = min((i + 1) * segment_length_s, duration_s)
                    output_filename = f"{output_prefix}_{str(i + 1).zfill(3)}{source_ext}"
                    output_path = os.path.join(temp_dir, output_filename)
                    await loop.run_in_executor(
                        None, partial(extract_audio, file_path, output_path, start_time, end_time)
                    )
                    output_files.append(output_path)
            elif source_ext != os.path.splitext(file_path)[1].lower():
                # Short file sent as-is, so it needs the alias to be accepted.
                output_files = [_aliased_upload_path(file_path, temp_dir)]
            else:
                output_files = [file_path]

            # Determine STT model from config. An explicit audio model is
            # honored or raises: no silent fallback to the default model.
            stt_config = {"timeout": config.stt_timeout} if config.stt_timeout else {}
            if config.audio_provider and config.audio_model:
                logger.info(
                    f"Using custom audio model: {config.audio_provider}/{config.audio_model}"
                )
                speech_to_text_model = _create_stt_model(
                    config.audio_provider, config.audio_model, stt_config
                )
            else:
                speech_to_text_model = _create_stt_model(
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
