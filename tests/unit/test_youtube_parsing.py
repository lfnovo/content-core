"""Unit tests for content_core.processors.url.youtube."""

import http.cookiejar
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from content_core.common.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidInputError,
    NoTranscriptFound,
)
from content_core.config import ContentCoreConfig
from content_core.processors.url.youtube import (
    _build_transcript_api,
    _fetch_transcript_pytubefix,
    _extract_youtube_id,
    extract_youtube,
)

# Dummy values only -- never real cookies in fixtures.
DUMMY_COOKIE_VALUE = "dummy-cookie-value-not-a-secret"
DUMMY_PROXY = "http://user:pass@proxy.example.invalid:8080"


@pytest.fixture
def cookies_file(tmp_path):
    path = tmp_path / "cookies.txt"
    path.write_text(
        "# Netscape HTTP Cookie File\n"
        f".youtube.com\tTRUE\t/\tTRUE\t0\tDUMMY\t{DUMMY_COOKIE_VALUE}\n"
    )
    return path


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

    async def test_no_transcript_on_either_path_raises(self, config):
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
            with pytest.raises(NoTranscriptFound):
                await extract_youtube(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", config
                )

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
            with pytest.raises(NoTranscriptFound):
                await extract_youtube(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", custom_config
                )
            mock_transcript.assert_called_once_with(
                "dQw4w9WgXcQ", ["fr", "de"], api=ANY
            )
            mock_pytubefix.assert_called_once_with(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", ["fr", "de"], proxy=None
            )


class TestYoutubeCookiesAndProxy:
    def test_youtube_neither_set_instantiates_api_without_args(self):
        with patch(
            "content_core.processors.url.youtube.YouTubeTranscriptApi"
        ) as mock_api:
            _build_transcript_api(ContentCoreConfig())
        mock_api.assert_called_once_with()

    def test_youtube_cookies_file_loaded_into_session(self, cookies_file):
        config = ContentCoreConfig(youtube_cookies_file=str(cookies_file))
        with patch(
            "content_core.processors.url.youtube.YouTubeTranscriptApi"
        ) as mock_api:
            _build_transcript_api(config)

        kwargs = mock_api.call_args.kwargs
        assert set(kwargs) == {"http_client"}
        jar = kwargs["http_client"].cookies
        assert isinstance(jar, http.cookiejar.MozillaCookieJar)
        assert jar.filename == str(cookies_file)
        assert [(c.name, c.value) for c in jar] == [("DUMMY", DUMMY_COOKIE_VALUE)]

    def test_youtube_proxy_builds_generic_proxy_config(self):
        config = ContentCoreConfig(youtube_proxy=DUMMY_PROXY)
        with (
            patch(
                "content_core.processors.url.youtube.YouTubeTranscriptApi"
            ) as mock_api,
            patch(
                "content_core.processors.url.youtube.GenericProxyConfig"
            ) as mock_proxy,
        ):
            _build_transcript_api(config)

        mock_proxy.assert_called_once_with(http_url=DUMMY_PROXY, https_url=DUMMY_PROXY)
        mock_api.assert_called_once_with(proxy_config=mock_proxy.return_value)

    def test_youtube_cookies_and_proxy_together(self, cookies_file):
        config = ContentCoreConfig(
            youtube_cookies_file=str(cookies_file), youtube_proxy=DUMMY_PROXY
        )
        with patch(
            "content_core.processors.url.youtube.YouTubeTranscriptApi"
        ) as mock_api:
            _build_transcript_api(config)

        assert set(mock_api.call_args.kwargs) == {"http_client", "proxy_config"}

    def test_youtube_missing_cookies_file_raises(self, tmp_path):
        config = ContentCoreConfig(youtube_cookies_file=str(tmp_path / "nope.txt"))
        with pytest.raises(ConfigurationError, match="nope.txt"):
            _build_transcript_api(config)

    def test_youtube_malformed_cookies_file_raises_without_leaking(self, tmp_path):
        path = tmp_path / "cookies.txt"
        path.write_text(f"not a cookies file\tSECRET={DUMMY_COOKIE_VALUE}\n")
        config = ContentCoreConfig(youtube_cookies_file=str(path))
        with pytest.raises(ConfigurationError) as exc_info:
            _build_transcript_api(config)
        assert DUMMY_COOKIE_VALUE not in str(exc_info.value)
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__

    async def test_youtube_missing_cookies_file_raises_from_extract(self, tmp_path):
        config = ContentCoreConfig(youtube_cookies_file=str(tmp_path / "nope.txt"))
        with patch(
            "content_core.processors.url.youtube.get_best_transcript",
            new_callable=AsyncMock,
        ) as mock_transcript:
            with pytest.raises(ConfigurationError):
                await extract_youtube(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", config
                )
        mock_transcript.assert_not_called()

    async def test_youtube_cookie_values_not_logged(self, cookies_file):
        from content_core.logging import logger

        messages = []
        logger.enable("content_core")
        sink_id = logger.add(messages.append, level="DEBUG")
        try:
            config = ContentCoreConfig(
                youtube_cookies_file=str(cookies_file), youtube_proxy=DUMMY_PROXY
            )
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
                with pytest.raises(NoTranscriptFound):
                    await extract_youtube(
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", config
                    )
        finally:
            logger.remove(sink_id)
            logger.disable("content_core")

        logged = "".join(str(m) for m in messages)
        assert str(cookies_file) in logged
        assert DUMMY_COOKIE_VALUE not in logged
        assert "user:pass" not in logged

    async def test_youtube_proxy_passed_to_both_paths(self):
        config = ContentCoreConfig(youtube_proxy=DUMMY_PROXY)
        with (
            patch(
                "content_core.processors.url.youtube.YouTubeTranscriptApi"
            ) as mock_api,
            patch(
                "content_core.processors.url.youtube.GenericProxyConfig"
            ) as mock_proxy,
            patch(
                "content_core.processors.url.youtube.get_best_transcript",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_transcript,
            patch(
                "content_core.processors.url.youtube.get_video_title",
                new_callable=AsyncMock,
                return_value="",
            ) as mock_title,
            patch(
                "content_core.processors.url.youtube.extract_transcript_pytubefix",
                return_value=(None, None),
            ) as mock_pytubefix,
        ):
            with pytest.raises(NoTranscriptFound):
                await extract_youtube(
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ", config
                )

        assert mock_title.call_args.kwargs["proxy"] == DUMMY_PROXY
        mock_proxy.assert_called_once_with(http_url=DUMMY_PROXY, https_url=DUMMY_PROXY)
        mock_api.assert_called_once_with(proxy_config=mock_proxy.return_value)
        assert mock_transcript.call_args.kwargs["api"] is mock_api.return_value
        assert mock_pytubefix.call_args.kwargs["proxy"] == DUMMY_PROXY

    async def test_youtube_proxy_passed_to_title_fetch(self):
        from content_core.processors.url.youtube import get_video_title

        response = MagicMock()
        response.text = AsyncMock(
            return_value='<meta property="og:title" content="A title">'
        )
        session = MagicMock()
        session.get.return_value.__aenter__ = AsyncMock(return_value=response)
        session.get.return_value.__aexit__ = AsyncMock(return_value=False)
        with patch(
            "content_core.processors.url.youtube.aiohttp.ClientSession"
        ) as mock_session_cls:
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            title = await get_video_title("dQw4w9WgXcQ", proxy=DUMMY_PROXY)

        assert title == "A title"
        assert session.get.call_args.kwargs["proxy"] == DUMMY_PROXY

    def test_youtube_pytubefix_receives_proxies(self):
        with patch("pytubefix.YouTube") as mock_yt:
            mock_yt.return_value.captions = {}
            _fetch_transcript_pytubefix(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", ["en"], DUMMY_PROXY
            )
        mock_yt.assert_called_once_with(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            proxies={"http": DUMMY_PROXY, "https": DUMMY_PROXY},
        )

    def test_youtube_pytubefix_without_proxy_unchanged(self):
        with patch("pytubefix.YouTube") as mock_yt:
            mock_yt.return_value.captions = {}
            _fetch_transcript_pytubefix(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ", ["en"]
            )
        mock_yt.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


class TestYoutubeTotalFailure:
    """Both transcript paths failing raises typed; one path failing degrades."""

    URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def _patches(self, primary, fallback):
        primary_kw = (
            {"side_effect": primary}
            if isinstance(primary, BaseException)
            else {"return_value": primary}
        )
        fallback_kw = (
            {"side_effect": fallback}
            if isinstance(fallback, BaseException)
            else {"return_value": fallback}
        )
        return (
            patch(
                "content_core.processors.url.youtube.get_best_transcript",
                new_callable=AsyncMock,
                **primary_kw,
            ),
            patch(
                "content_core.processors.url.youtube.get_video_title",
                new_callable=AsyncMock,
                return_value="",
            ),
            patch(
                "content_core.processors.url.youtube.extract_transcript_pytubefix",
                **fallback_kw,
            ),
        )

    async def test_blocked_on_both_paths_raises_external_service_error(self):
        blocked = RuntimeError("IpBlocked: YouTube is blocking requests from your IP")
        p1, p2, p3 = self._patches(blocked, RuntimeError("blocked too"))
        with p1, p2, p3, pytest.raises(ExternalServiceError) as exc_info:
            await extract_youtube(self.URL, ContentCoreConfig())
        assert exc_info.value.__cause__ is blocked

    async def test_fallback_error_wins_over_no_transcript(self):
        fallback_error = RuntimeError("pytubefix bot check")
        p1, p2, p3 = self._patches(NoTranscriptFound("none"), fallback_error)
        with p1, p2, p3, pytest.raises(ExternalServiceError) as exc_info:
            await extract_youtube(self.URL, ContentCoreConfig())
        assert exc_info.value.__cause__ is fallback_error

    async def test_no_transcript_on_both_paths_raises_no_transcript_found(self):
        p1, p2, p3 = self._patches(NoTranscriptFound("none"), (None, None))
        with p1, p2, p3, pytest.raises(NoTranscriptFound):
            await extract_youtube(self.URL, ContentCoreConfig())

    async def test_primary_failure_degrades_to_pytubefix(self):
        p1, p2, p3 = self._patches(RuntimeError("IpBlocked"), ("Fallback text", "srt"))
        with p1, p2, p3:
            result = await extract_youtube(self.URL, ContentCoreConfig())
        assert result.content == "Fallback text"

    async def test_url_without_video_id_raises_invalid_input(self):
        with pytest.raises(InvalidInputError):
            await extract_youtube(
                "https://www.youtube.com/@somechannel", ContentCoreConfig()
            )

    async def test_primary_block_with_captionless_fallback_raises_external(self):
        blocked = RuntimeError("IpBlocked")
        p1, p2, p3 = self._patches(blocked, (None, None))
        with p1, p2, p3, pytest.raises(ExternalServiceError) as exc_info:
            await extract_youtube(self.URL, ContentCoreConfig())
        assert exc_info.value.__cause__ is blocked

    async def test_formatter_failure_is_not_reported_as_no_transcript(self):
        transcript = MagicMock()
        transcript.snippets = []
        p1, p2, p3 = self._patches(transcript, (None, None))
        with (
            p1,
            p2,
            p3,
            patch("content_core.processors.url.youtube.TextFormatter") as fmt,
            pytest.raises(ExternalServiceError),
        ):
            fmt.return_value.format_transcript.side_effect = ValueError("bad data")
            await extract_youtube(self.URL, ContentCoreConfig())


class TestFetchBestTranscriptErrors:
    """A failed fetch is not collapsed into "no transcript"."""

    async def test_blocked_fetch_is_reraised(self):
        import youtube_transcript_api as yta

        api = MagicMock()
        transcript_list = api.list.return_value
        for finder in (
            transcript_list.find_manually_created_transcript,
            transcript_list.find_generated_transcript,
            transcript_list.find_transcript,
        ):
            finder.return_value.fetch.side_effect = RuntimeError("IpBlocked")
        api.fetch.side_effect = yta.NoTranscriptFound("vid", ["en"], MagicMock())

        from content_core.processors.url.youtube import _fetch_best_transcript

        # __wrapped__ skips the retry decorator: this tests classification only.
        with pytest.raises(RuntimeError, match="IpBlocked"):
            await _fetch_best_transcript.__wrapped__("vid", ["en"], api)

    async def test_transcripts_disabled_is_no_transcript_found(self):
        import youtube_transcript_api as yta

        api = MagicMock()
        api.list.side_effect = yta.TranscriptsDisabled("vid")

        from content_core.processors.url.youtube import _fetch_best_transcript

        with pytest.raises(NoTranscriptFound):
            await _fetch_best_transcript.__wrapped__("vid", ["en"], api)

    async def test_no_transcript_anywhere_is_no_transcript_found(self):
        import youtube_transcript_api as yta

        not_found = yta.NoTranscriptFound("vid", ["en"], MagicMock())
        api = MagicMock()
        transcript_list = api.list.return_value
        transcript_list.find_manually_created_transcript.side_effect = not_found
        transcript_list.find_generated_transcript.side_effect = not_found
        transcript_list.find_transcript.side_effect = not_found
        api.fetch.side_effect = not_found

        from content_core.processors.url.youtube import _fetch_best_transcript

        with pytest.raises(NoTranscriptFound):
            await _fetch_best_transcript.__wrapped__("vid", ["en"], api)
