import asyncio
import math
import os
import tempfile
import traceback
from functools import partial

from moviepy import AudioFileClip

from content_core.common import ProcessSourceState
from content_core.logging import logger

# todo: remove reference to model_manager
# future: parallelize the transcription process


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
            output_filename = f"{output_prefix}_{str(i+1).zfill(3)}.mp3"
            output_path = os.path.join(output_dir, output_filename)

            # Export segment
            extract_audio(input_file_abs, output_path, start_time, end_time)

            output_files.append(output_path)

            logger.debug(f"Exported segment {i+1}/{total_segments}: {output_filename}")

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


async def transcribe_audio_segment(audio_file, model):
    """Transcribe a single audio segment asynchronously"""
    return (await model.atranscribe(audio_file)).text


async def extract_audio_data(data: ProcessSourceState):
    input_audio_path = data.file_path

    try:
        # Create a temporary directory for audio segments
        temp_dir = tempfile.mkdtemp()
        output_prefix = os.path.splitext(os.path.basename(input_audio_path))[0]
        output_dir = temp_dir
        os.makedirs(output_dir, exist_ok=True)

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
                output_filename = f"{output_prefix}_{str(i+1).zfill(3)}.mp3"
                output_path = os.path.join(output_dir, output_filename)

                extract_audio(input_audio_path, output_path, start_time, end_time)

                output_files.append(output_path)
        else:
            output_files = [input_audio_path]

        # Transcribe audio files
        from content_core.models import ModelFactory

        speech_to_text_model = ModelFactory.get_model("speech_to_text")
        transcriptions = []
        for audio_file in output_files:
            transcription = await transcribe_audio_segment(
                audio_file, speech_to_text_model
            )
            transcriptions.append(transcription)

        return {
            "metadata": {"audio_files": output_files},
            "content": " ".join(transcriptions),
        }
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        logger.error(traceback.format_exc())
        raise
