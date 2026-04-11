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

        mock_audio_clip = MagicMock()
        mock_audio_clip.duration = 60  # 1 minute, no splitting needed
        mock_audio_clip.close = MagicMock()

        with (
            patch(
                "esperanto.AIFactory"
            ) as mock_factory,
            patch(
                "content_core.processors.media.audio.AudioFileClip",
                return_value=mock_audio_clip,
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

        mock_audio_clip = MagicMock()
        mock_audio_clip.duration = 60
        mock_audio_clip.close = MagicMock()

        with (
            patch(
                "esperanto.AIFactory"
            ) as mock_factory,
            patch(
                "content_core.processors.media.audio.AudioFileClip",
                return_value=mock_audio_clip,
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

        mock_audio_clip = MagicMock()
        mock_audio_clip.duration = 60
        mock_audio_clip.close = MagicMock()

        with (
            patch(
                "esperanto.AIFactory"
            ) as mock_factory,
            patch(
                "content_core.processors.media.audio.AudioFileClip",
                return_value=mock_audio_clip,
            ),
        ):
            mock_factory.create_speech_to_text.return_value = mock_stt_model

            from content_core.processors.media.audio import transcribe_audio

            await transcribe_audio("/fake/audio.mp3", config)
            mock_factory.create_speech_to_text.assert_called_once_with(
                "deepgram", "nova-2", {"timeout": 1800}
            )


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
        # Second stream has highest bit_rate + channels + sample_rate
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
