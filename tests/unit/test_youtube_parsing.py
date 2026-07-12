"""Unit tests for content_core.processors.url.youtube."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.url.youtube import _extract_youtube_id, extract_youtube


class TestExtractYoutubeId:
    async def test_standard_watch_url(self):
        result = await _extract_youtube_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert result == "dQw4w9WgXcQ"

    async def test_short_url(self):
        result = await _extract_youtube_id("https://youtu.be/dQw4w9WgXcQ")
        assert result == "dQw4w9WgXcQ"

    async def test_embed_url(self):
        result = await _extract_youtube_id(
            "https://www.youtube.com/embed/dQw4w9WgXcQ"
        )
        assert result == "dQw4w9WgXcQ"

    async def test_live_url(self):
        result = await _extract_youtube_id(
            "https://www.youtube.com/live/dQw4w9WgXcQ"
        )
        assert result == "dQw4w9WgXcQ"

    async def test_shorts_url(self):
        result = await _extract_youtube_id(
            "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        )
        assert result == "dQw4w9WgXcQ"

    async def test_url_with_extra_params(self):
        result = await _extract_youtube_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120"
        )
        assert result == "dQw4w9WgXcQ"

    async def test_non_youtube_url_returns_none(self):
        result = await _extract_youtube_id("https://example.com")
        assert result is None


class TestExtractYoutube:
    @pytest.fixture
    def config(self):
        return ContentCoreConfig(youtube_languages=["en", "es", "pt"])

    async def test_successful_extraction(self, config):
        mock_snippet = MagicMock()
        mock_snippet.text = "Hello world"
        mock_snippet.start = 0.0
        mock_snippet.duration = 5.0

        mock_transcript = MagicMock()
        mock_transcript.snippets = [mock_snippet]

        with (
            patch(
                "content_core.processors.url.youtube.get_best_transcript",
                new_callable=AsyncMock,
                return_value=mock_transcript,
            ),
            patch(
                "content_core.processors.url.youtube.get_video_title",
                new_callable=AsyncMock,
                return_value="Test Video Title",
            ),
            patch(
                "content_core.processors.url.youtube.TextFormatter"
            ) as mock_formatter_cls,
        ):
            mock_formatter_cls.return_value.format_transcript.return_value = (
                "Hello world"
            )

            result = await extract_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", config
            )
            assert result.content == "Hello world"
            assert result.title == "Test Video Title"
            assert result.source_type == "url"
            assert result.identified_type == "youtube"
            assert result.metadata["video_id"] == "dQw4w9WgXcQ"

    async def test_transcript_failure_with_pytubefix_fallback(self, config):
        with (
            patch(
                "content_core.processors.url.youtube.get_best_transcript",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "content_core.processors.url.youtube.get_video_title",
                new_callable=AsyncMock,
                return_value="Fallback Video",
            ),
            patch(
                "content_core.processors.url.youtube.extract_transcript_pytubefix",
                return_value=("Fallback transcript", "raw srt"),
            ),
        ):
            result = await extract_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", config
            )
            assert result.content == "Fallback transcript"
            assert result.title == "Fallback Video"

    async def test_both_failures_returns_empty(self, config):
        with (
            patch(
                "content_core.processors.url.youtube.get_best_transcript",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "content_core.processors.url.youtube.get_video_title",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "content_core.processors.url.youtube.extract_transcript_pytubefix",
                return_value=(None, None),
            ),
        ):
            result = await extract_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", config
            )
            assert result.content == ""

    async def test_uses_config_languages(self):
        custom_config = ContentCoreConfig(youtube_languages=["fr", "de"])

        with (
            patch(
                "content_core.processors.url.youtube.get_best_transcript",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_transcript,
            patch(
                "content_core.processors.url.youtube.get_video_title",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "content_core.processors.url.youtube.extract_transcript_pytubefix",
                return_value=(None, None),
            ) as mock_pytubefix,
        ):
            await extract_youtube(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", custom_config
            )
            mock_transcript.assert_called_once_with("dQw4w9WgXcQ", ["fr", "de"])
            mock_pytubefix.assert_called_once_with(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", ["fr", "de"]
            )
