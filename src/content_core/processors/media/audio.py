import asyncio
import json
import math
import os
import shutil
import subprocess
import tempfile
from functools import partial
from pathlib import Path

import httpx

from content_core.common.exceptions import (
    ConfigurationError,
    ContentCoreError,
    ExternalServiceError,
    AudioTranscriptionError,
    FileOperationError,
)
from content_core.common.retry import retry_audio_transcription
from content_core.config import ContentCoreConfig
from content_core.processors.media.checkpoint import AudioCheckpoint
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


async def _transcribe_segment(audio_file, model, language=None):
    """Transcribe once; retry policy is selected by the caller."""
    kwargs = {"language": language} if language else {}
    return (await model.atranscribe(audio_file, **kwargs)).text


async def transcribe_audio_segment(
    audio_file, model, semaphore, *, max_attempts=None, language=None, before_attempt=None
):
    """Transcribe a single audio segment with concurrency control and retry logic.

    Raises ExternalServiceError once the provider still fails after retries.
    """
    async with semaphore:
        try:
            # STT calls can be billed even when their response is lost. Never
            # replay one implicitly; applications may opt in explicitly.
            attempts = 1 if max_attempts is None else max_attempts
            async def transcribe():
                if before_attempt is not None:
                    await before_attempt()
                if language:
                    return await _transcribe_segment(audio_file, model, language)
                return await _transcribe_segment(audio_file, model)

            if attempts == 1:
                return await transcribe()
            return await retry_audio_transcription(max_attempts=attempts)(transcribe)()
        except ContentCoreError:
            raise
        except Exception as e:
            raise ExternalServiceError(
                "Speech-to-text failed. Check the provider before resubmitting; "
                "the request may already have been billed."
            ) from e


def _create_stt_model(provider: str, model: str, stt_config: dict):
    from esperanto import AIFactory

    try:
        return AIFactory.create_speech_to_text(provider, model, stt_config)
    except Exception as e:
        raise ConfigurationError(
            f"Could not create speech-to-text model {provider}/{model}. "
            "Check its credentials and endpoint."
        ) from e


async def transcribe_audio(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Transcribe an audio file using STT.

    Raises:
        FileOperationError: ffmpeg/ffprobe could not read or split the file.
        ConfigurationError: the STT model could not be created.
        ExternalServiceError: the STT provider failed after retries.
    """
    checkpoint = None
    speech_to_text_model = None
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
            # Split oversized chunks again before any potentially billed call.
            # Recursion retains chronological left/right order and works for
            # variable-bit-rate recordings without guessing duration from bytes.
            async def fit_upload(path, depth=0):
                limit = config.audio_max_upload_bytes
                if limit is None or os.path.getsize(path) <= limit:
                    return [path]
                duration = await get_audio_duration(path)
                if depth >= 20 or duration <= 0.1:
                    raise FileOperationError(
                        "Cannot split audio below the upload limit; re-encode the recording."
                    )
                parts = []
                for index, (start, end) in enumerate(
                    ((0, duration / 2), (duration / 2, duration))
                ):
                    output = os.path.join(
                        temp_dir, f"{Path(path).stem}_part{index}{source_ext}"
                    )
                    await asyncio.get_running_loop().run_in_executor(
                        None, partial(extract_audio, path, output, start, end)
                    )
                    parts.extend(await fit_upload(output, depth + 1))
                return parts

            bounded_files = []
            for path in output_files:
                bounded_files.extend(await fit_upload(path))
            output_files = bounded_files

            stt_config = dict(config.stt_config)
            if config.stt_timeout:
                stt_config.setdefault("timeout", config.stt_timeout)
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

            if config.audio_checkpoint_dir:
                # Never store credentials: they participate only in the digest.
                # Different source bytes, language, endpoint or key cannot reuse
                # another transcription's text.
                checkpoint = AudioCheckpoint(
                    config.audio_checkpoint_dir, file_path,
                    {"version": 1, "provider": config.audio_provider,
                     "model": config.audio_model, "fallback_provider": config.stt_provider,
                     "fallback_model": config.stt_model, "language": config.audio_language,
                     "segment_minutes": config.audio_segment_minutes,
                     "upload_limit": config.audio_max_upload_bytes,
                     "stt_config": config.stt_config,
                     "effective_key": getattr(speech_to_text_model, "api_key", None),
                     "effective_endpoint": getattr(speech_to_text_model, "base_url", None)},
                )

            # Validate all saved entries before making any paid requests.
            cached_chunks = [
                checkpoint.read(index, path) if checkpoint is not None else (None, None)
                for index, path in enumerate(output_files)
            ]
            saved_before_run = sum(text is not None for _, text in cached_chunks)

            concurrency = config.audio_concurrency
            semaphore = asyncio.Semaphore(concurrency)

            logger.debug(
                f"Transcribing {len(output_files)} audio segments with concurrency limit of {concurrency}"
            )

            stopped = asyncio.Event()
            reused = 0
            newly_saved = 0
            request_lock = asyncio.Lock()
            next_request_at = 0.0

            async def process_segment(index, audio_file):
                nonlocal reused, newly_saved, next_request_at
                async with semaphore:
                    key, cached = cached_chunks[index]
                    if cached is not None:
                        reused += 1
                        logger.info(f"Reusing saved audio chunk {index + 1}/{len(output_files)}")
                        return cached
                    if stopped.is_set():
                        return None
                    try:
                        async def pace_request():
                            """Gate every billed attempt, including opt-in retries."""
                            nonlocal next_request_at
                            if stopped.is_set():
                                raise ExternalServiceError(
                                    "Audio transcription stopped after another chunk failed."
                                )
                            # Pace request starts, independently of concurrency.
                            # Cached chunks do not consume a slot or add a delay.
                            async with request_lock:
                                loop = asyncio.get_running_loop()
                                delay = next_request_at - loop.time()
                                if delay > 0:
                                    await asyncio.sleep(delay)
                                if stopped.is_set():
                                    raise ExternalServiceError(
                                        "Audio transcription stopped after another chunk failed."
                                    )
                                next_request_at = (
                                    loop.time() + config.audio_request_interval_seconds
                                )

                        text = await transcribe_audio_segment(
                            audio_file, speech_to_text_model, asyncio.Semaphore(1),
                            max_attempts=config.audio_transcription_attempts,
                            language=config.audio_language,
                            before_attempt=pace_request,
                        )
                        if checkpoint is not None:
                            checkpoint.save(key, text)
                            newly_saved += 1
                            logger.info(f"Saved audio chunk {index + 1}/{len(output_files)}")
                        return text
                    except BaseException:
                        stopped.set()
                        raise

            transcription_tasks = [
                process_segment(index, audio_file)
                for index, audio_file in enumerate(output_files)
            ]

            # Drain in-flight work before temporary files are removed. gather
            # preserves input order even when later segments finish first.
            transcriptions = await asyncio.gather(
                *transcription_tasks, return_exceptions=True
            )
            for index, result in enumerate(transcriptions):
                if isinstance(result, BaseException):
                    if checkpoint is not None and isinstance(result, ExternalServiceError):
                        status = None
                        cause = result
                        # Inspect only numeric status, never expose upstream text.
                        for _ in range(8):
                            candidate = getattr(cause, "status_code", None)
                            if isinstance(candidate, int) and 400 <= candidate <= 599:
                                status = candidate
                                break
                            cause = cause.__cause__
                            if cause is None:
                                break
                        raise AudioTranscriptionError(
                            index + 1, len(output_files), saved_before_run + newly_saved, status
                        ) from result
                    raise result

            logger.info(f"Audio transcription complete: {len(output_files)} chunks, {reused} reused")
            return ExtractionOutput(
                content=" ".join(transcriptions),
                source_type="file",
                identified_type="audio/*",
                metadata={"segments_count": len(output_files), "segments_reused": reused},
            )
    except Exception:
        logger.error("Audio extraction failed; no partial transcript returned")
        raise
    finally:
        if checkpoint is not None:
            checkpoint.close()
        # Provider instances own both clients, including checkpoint-only runs.
        if speech_to_text_model is not None:
            sync_client = getattr(speech_to_text_model, "client", None)
            async_client = getattr(speech_to_text_model, "async_client", None)
            try:
                if isinstance(sync_client, httpx.Client):
                    sync_client.close()
            except Exception:
                logger.warning("Could not close an audio provider client")
            try:
                if isinstance(async_client, httpx.AsyncClient):
                    await async_client.aclose()
            except Exception:
                logger.warning("Could not close an audio provider client")
