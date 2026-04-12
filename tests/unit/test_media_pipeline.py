"""Unit tests for content_core.processors.media (audio + video)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.common.state import ExtractionOutput
from content_core.processors.media.video import (
    extract_video,
    get_audio_streams,
    select_best_audio_stream,
)


def _ffprobe_duration_result(duration: float):
    """Helper: build a mock subprocess result for ffprobe duration query."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = json.dumps({"format": {"duration": str(duration)}})
    return mock


class TestTranscribeAudio:
    @pytest.fixture
    def config(self):
        return ContentCoreConfig(
            stt_provider="openai",
            stt_model="whisper-1",
            audio_provider="openai",
            audio_model=None,
        )

    async def test_transcribe_with_default_stt(self, config):
        mock_stt_model = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Transcribed text"
        mock_stt_model.atranscribe = AsyncMock(return_value=mock_result)

        with (
            patch("esperanto.AIFactory") as mock_factory,
            patch(
                "content_core.processors.media.audio.get_audio_duration",
                new_callable=AsyncMock,
                return_value=60.0,
            ),
        ):
            mock_factory.create_speech_to_text.return_value = mock_stt_model

            from content_core.processors.media.audio import transcribe_audio

            result = await transcribe_audio("/fake/audio.mp3", config)
            assert result.content == "Transcribed text"
            assert result.source_type == "file"
            assert result.identified_type == "audio/*"
            mock_factory.create_speech_to_text.assert_called_once_with(
                "openai", "whisper-1", {"timeout": 3600}
            )

    async def test_transcribe_with_custom_audio_model(self):
        custom_config = ContentCoreConfig(
            audio_provider="groq",
            audio_model="whisper-large-v3",
            stt_provider="openai",
            stt_model="whisper-1",
        )

        mock_stt_model = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Custom transcription"
        mock_stt_model.atranscribe = AsyncMock(return_value=mock_result)

        with (
            patch("esperanto.AIFactory") as mock_factory,
            patch(
                "content_core.processors.media.audio.get_audio_duration",
                new_callable=AsyncMock,
                return_value=60.0,
            ),
        ):
            mock_factory.create_speech_to_text.return_value = mock_stt_model

            from content_core.processors.media.audio import transcribe_audio

            result = await transcribe_audio("/fake/audio.mp3", custom_config)
            assert result.content == "Custom transcription"
            mock_factory.create_speech_to_text.assert_called_once_with(
                "groq", "whisper-large-v3", {"timeout": 3600}
            )

    async def test_transcribe_uses_stt_config_when_no_custom_model(self):
        config = ContentCoreConfig(
            audio_provider="openai",
            audio_model=None,
            stt_provider="deepgram",
            stt_model="nova-2",
            stt_timeout=1800,
        )

        mock_stt_model = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Result"
        mock_stt_model.atranscribe = AsyncMock(return_value=mock_result)

        with (
            patch("esperanto.AIFactory") as mock_factory,
            patch(
                "content_core.processors.media.audio.get_audio_duration",
                new_callable=AsyncMock,
                return_value=60.0,
            ),
        ):
            mock_factory.create_speech_to_text.return_value = mock_stt_model

            from content_core.processors.media.audio import transcribe_audio

            await transcribe_audio("/fake/audio.mp3", config)
            mock_factory.create_speech_to_text.assert_called_once_with(
                "deepgram", "nova-2", {"timeout": 1800}
            )

    async def test_transcribe_splits_long_audio(self):
        config = ContentCoreConfig(
            stt_provider="openai",
            stt_model="whisper-1",
            audio_provider="openai",
            audio_model=None,
        )

        mock_stt_model = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "segment"
        mock_stt_model.atranscribe = AsyncMock(return_value=mock_result)

        with (
            patch("esperanto.AIFactory") as mock_factory,
            patch(
                "content_core.processors.media.audio.get_audio_duration",
                new_callable=AsyncMock,
                return_value=1500.0,  # 25 minutes → 3 segments
            ),
            patch(
                "content_core.processors.media.audio.extract_audio"
            ) as mock_extract,
        ):
            mock_factory.create_speech_to_text.return_value = mock_stt_model

            from content_core.processors.media.audio import transcribe_audio

            result = await transcribe_audio("/fake/long_audio.mp3", config)
            assert result.content == "segment segment segment"
            assert result.metadata["segments_count"] == 3
            assert mock_extract.call_count == 3


class TestGetAudioDuration:
    async def test_returns_duration_from_ffprobe(self):
        with patch(
            "content_core.processors.media.audio.asyncio.get_event_loop"
        ) as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=123.45)

            from content_core.processors.media.audio import get_audio_duration

            result = await get_audio_duration("/fake/audio.mp3")
            assert result == 123.45


class TestExtractAudio:
    def test_calls_ffmpeg_with_time_range(self):
        with patch(
            "content_core.processors.media.audio.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            from content_core.processors.media.audio import extract_audio

            extract_audio("/in.mp3", "/out.mp3", start_time=10.0, end_time=60.0)
            cmd = mock_run.call_args[0][0]
            assert "-ss" in cmd
            assert "-to" in cmd
            assert "-codec" in cmd
            assert "-map_chapters" in cmd

    def test_calls_ffmpeg_without_time_range(self):
        with patch(
            "content_core.processors.media.audio.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            from content_core.processors.media.audio import extract_audio

            extract_audio("/in.mp3", "/out.mp3")
            cmd = mock_run.call_args[0][0]
            assert "-ss" not in cmd
            assert "-to" not in cmd

    def test_raises_on_ffmpeg_failure(self):
        with patch(
            "content_core.processors.media.audio.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error msg")

            from content_core.processors.media.audio import extract_audio

            with pytest.raises(RuntimeError, match="ffmpeg extract failed"):
                extract_audio("/in.mp3", "/out.mp3")


class TestExtractVideo:
    @pytest.fixture
    def config(self):
        return ContentCoreConfig()

    async def test_successful_video_extraction(self, config):
        streams = [
            {"bit_rate": "128000", "channels": 2, "sample_rate": "44100"}
        ]

        with (
            patch("os.path.exists", return_value=True),
            patch(
                "content_core.processors.media.video.get_audio_streams",
                new_callable=AsyncMock,
                return_value=streams,
            ),
            patch(
                "content_core.processors.media.video.select_best_audio_stream",
                new_callable=AsyncMock,
                return_value=streams[0],
            ),
            patch(
                "content_core.processors.media.video.extract_audio_from_video",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "content_core.processors.media.audio.transcribe_audio",
                new_callable=AsyncMock,
                return_value=ExtractionOutput(
                    content="Video transcription",
                    source_type="file",
                    identified_type="audio/*",
                    metadata={"segments_count": 1},
                ),
            ),
        ):
            result = await extract_video("/fake/video.mp4", config)
            assert result.content == "Video transcription"
            assert result.source_type == "file"
            assert result.identified_type == "video/*"

    async def test_no_audio_streams(self, config):
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "content_core.processors.media.video.get_audio_streams",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result = await extract_video("/fake/silent.mp4", config)
            assert result.content == ""
            assert "No audio streams" in result.metadata["error"]

    async def test_file_not_found_raises(self, config):
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FileNotFoundError):
                await extract_video("/no/such/video.mp4", config)


class TestSelectBestAudioStream:
    async def test_picks_best_quality(self):
        streams = [
            {"bit_rate": "64000", "channels": 1, "sample_rate": "22050"},
            {"bit_rate": "320000", "channels": 2, "sample_rate": "48000"},
            {"bit_rate": "128000", "channels": 2, "sample_rate": "44100"},
        ]
        result = await select_best_audio_stream(streams)
        assert result["bit_rate"] == "320000"

    async def test_empty_list_returns_none(self):
        result = await select_best_audio_stream([])
        assert result is None


class TestGetAudioStreams:
    async def test_parses_ffprobe_output(self):
        ffprobe_output = json.dumps(
            {
                "streams": [
                    {
                        "codec_type": "audio",
                        "bit_rate": "128000",
                        "channels": 2,
                        "sample_rate": "44100",
                    }
                ]
            }
        )

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ffprobe_output

        with patch(
            "content_core.processors.media.video.asyncio.get_event_loop"
        ) as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=[
                    {
                        "codec_type": "audio",
                        "bit_rate": "128000",
                        "channels": 2,
                        "sample_rate": "44100",
                    }
                ]
            )
            result = await get_audio_streams("/fake/video.mp4")
            assert len(result) == 1
            assert result[0]["channels"] == 2
