import asyncio
import math
import os
import tempfile
import traceback
from functools import partial

from moviepy import AudioFileClip

from content_core.common import ProcessSourceState
from content_core.common.retry import retry_audio_transcription
from content_core.config import get_audio_concurrency
from content_core.logging import logger


async def split_audio(input_file, segment_length_minutes=15, output_prefix=None):
    """
    Split an audio file into segments asynchronously.
    """

    def _split(input_file, segment_length_minutes, output_prefix):
        # Convert input file to absolute path
        input_file_abs = os.path.abspath(input_file)
        output_dir = os.path.dirname(input_file_abs)
        os.makedirs(output_dir, exist_ok=True)

        # Set up output prefix
        if output_prefix is None:
            output_prefix = os.path.splitext(os.path.basename(input_file_abs))[0]

        # Load the audio file
        audio = AudioFileClip(input_file_abs)

        # Calculate segment length in seconds
        segment_length_s = segment_length_minutes * 60

        # Calculate number of segments
        total_segments = math.ceil(audio.duration / segment_length_s)
        logger.debug(f"Splitting file: {input_file_abs} into {total_segments} segments")

        output_files = []

        # Split the audio into segments
        for i in range(total_segments):
            start_time = i * segment_length_s
            end_time = min((i + 1) * segment_length_s, audio.duration)

            # Extract segment
            output_filename = f"{output_prefix}_{str(i + 1).zfill(3)}.mp3"
            output_path = os.path.join(output_dir, output_filename)

            # Export segment
            extract_audio(input_file_abs, output_path, start_time, end_time)

            output_files.append(output_path)

            logger.debug(
                f"Exported segment {i + 1}/{total_segments}: {output_filename}"
            )

        return output_files

    # Run CPU-bound audio processing in thread pool
    return await asyncio.get_event_loop().run_in_executor(
        None, partial(_split, input_file, segment_length_minutes, output_prefix)
    )


def extract_audio(
    input_file: str, output_file: str, start_time: float = None, end_time: float = None
) -> None:
    """
    Extract audio from a video or audio file and save it as an MP3 file.
    If start_time and end_time are provided, only that segment of audio is extracted.

    Args:
        input_file (str): Path to the input video or audio file.
        output_file (str): Path where the output MP3 file will be saved.
        start_time (float, optional): Start time of the audio segment in seconds. Defaults to None.
        end_time (float, optional): End time of the audio segment in seconds. Defaults to None.
    """
    try:
        # Load the file as an AudioFileClip
        audio_clip = AudioFileClip(input_file)

        # If start_time and/or end_time are provided, trim the audio using subclipped
        if start_time is not None and end_time is not None:
            audio_clip = audio_clip.subclipped(start_time, end_time)
        elif start_time is not None:
            audio_clip = audio_clip.subclipped(start_time)
        elif end_time is not None:
            audio_clip = audio_clip.subclipped(0, end_time)

        # Export the audio as MP3
        audio_clip.write_audiofile(output_file, codec="mp3")
        audio_clip.close()
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        raise


@retry_audio_transcription()
async def _transcribe_segment(audio_file, model):
    """Internal function to transcribe a single segment - wrapped with retry logic."""
    return (await model.atranscribe(audio_file)).text


async def transcribe_audio_segment(audio_file, model, semaphore):
    """
    Transcribe a single audio segment asynchronously with concurrency control and retry logic.

    This function uses a semaphore to limit the number of concurrent transcriptions,
    preventing API rate limits while allowing parallel processing for improved performance.
    Includes retry logic for transient API failures.

    Args:
        audio_file (str): Path to the audio file segment to transcribe
        model: Speech-to-text model instance with atranscribe() method
        semaphore (asyncio.Semaphore): Semaphore to control concurrency

    Returns:
        str: Transcribed text from the audio segment

    Note:
        Multiple instances of this function can run concurrently, but the semaphore
        ensures that no more than N transcriptions happen simultaneously, where N
        is configured via get_audio_concurrency() (default: 3, range: 1-10).
    """
    async with semaphore:
        return await _transcribe_segment(audio_file, model)


async def extract_audio_data(data: ProcessSourceState):
    """
    Extract and transcribe audio from a file with automatic segmentation and parallel processing.

    This function handles the complete audio processing pipeline:
    1. Splits long audio files (>10 minutes) into segments
    2. Transcribes segments in parallel using configurable concurrency
    3. Joins transcriptions in correct order

    For files longer than 10 minutes, segments are processed concurrently with a
    configurable concurrency limit to balance performance and API rate limits.

    Args:
        data (ProcessSourceState): State object containing file_path to audio/video file

    Returns:
        dict: Dictionary containing:
            - metadata: Information about processed segments count
            - content: Complete transcribed text

    Configuration:
        Concurrency is controlled via:
        - Environment variable: CCORE_AUDIO_CONCURRENCY (1-10, default: 3)
        - YAML config: extraction.audio.concurrency

    Raises:
        Exception: If audio extraction or transcription fails
    """
    input_audio_path = data.file_path
    audio = None

    try:
        # Use TemporaryDirectory context manager for automatic cleanup
        with tempfile.TemporaryDirectory() as temp_dir:
            output_prefix = os.path.splitext(os.path.basename(input_audio_path))[0]
            output_dir = temp_dir

            # Split audio into segments if longer than 10 minutes
            audio = AudioFileClip(input_audio_path)
            duration_s = audio.duration
            segment_length_s = 10 * 60  # 10 minutes in seconds
            output_files = []

            if duration_s > segment_length_s:
                logger.info(
                    f"Audio is longer than 10 minutes ({duration_s}s), splitting into {math.ceil(duration_s / segment_length_s)} segments"
                )
                for i in range(math.ceil(duration_s / segment_length_s)):
                    start_time = i * segment_length_s
                    end_time = min((i + 1) * segment_length_s, audio.duration)

                    # Extract segment
                    output_filename = f"{output_prefix}_{str(i + 1).zfill(3)}.mp3"
                    output_path = os.path.join(output_dir, output_filename)

                    extract_audio(input_audio_path, output_path, start_time, end_time)

                    output_files.append(output_path)
            else:
                output_files = [input_audio_path]

            # Close audio clip after determining segments
            if audio:
                audio.close()
                audio = None

            # Transcribe audio files in parallel with concurrency limit
            from content_core.config import CONFIG
            from content_core.models import ModelFactory
            from esperanto import AIFactory

            # Determine which model to use based on state parameters
            if data.audio_provider and data.audio_model:
                # Custom model provided - create new instance
                try:
                    logger.info(
                        f"Using custom audio model: {data.audio_provider}/{data.audio_model}"
                    )
                    # Get timeout from config (same as default model) or use fallback
                    timeout = CONFIG.get('speech_to_text', {}).get('timeout', 3600)
                    stt_config = {'timeout': timeout} if timeout else {}
                    # Proxy is configured via HTTP_PROXY/HTTPS_PROXY env vars (handled by Esperanto)
                    speech_to_text_model = AIFactory.create_speech_to_text(
                        data.audio_provider, data.audio_model, stt_config
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create custom audio model '{data.audio_provider}/{data.audio_model}': {e}. "
                        f"Check that the provider and model are supported by Esperanto. "
                        f"Falling back to default model."
                    )
                    speech_to_text_model = ModelFactory.get_model("speech_to_text")
            elif data.audio_provider or data.audio_model:
                # Only one parameter provided - log warning and use default
                missing = "audio_model" if data.audio_provider else "audio_provider"
                provided = "audio_provider" if data.audio_provider else "audio_model"
                logger.warning(
                    f"{provided} provided without {missing}. "
                    f"Both audio_provider and audio_model must be specified together. "
                    f"Falling back to default model."
                )
                speech_to_text_model = ModelFactory.get_model("speech_to_text")
            else:
                # No custom parameters - use default (backward compatible)
                speech_to_text_model = ModelFactory.get_model("speech_to_text")

            concurrency = get_audio_concurrency()
            semaphore = asyncio.Semaphore(concurrency)

            logger.debug(
                f"Transcribing {len(output_files)} audio segments with concurrency limit of {concurrency}"
            )

            # Create tasks for parallel transcription
            transcription_tasks = [
                transcribe_audio_segment(audio_file, speech_to_text_model, semaphore)
                for audio_file in output_files
            ]

            # Execute all transcriptions concurrently (limited by semaphore)
            transcriptions = await asyncio.gather(*transcription_tasks)

            return {
                "metadata": {"segments_count": len(output_files)},
                "content": " ".join(transcriptions),
            }
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        # Ensure audio clip is closed even if an error occurs
        if audio:
            try:
                audio.close()
            except Exception:
                pass
