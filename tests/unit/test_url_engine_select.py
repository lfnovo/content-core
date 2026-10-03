"""Tests for URL engine selection logic in extract_from_url."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from content_core import extract_content
from content_core.common.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidInputError,
    NetworkError,
    NotFoundError,
)
from content_core.config import ContentCoreConfig
from content_core.common.state import ExtractionOutput
from content_core.processors.url import extract_from_url


def _http_error(status: int) -> aiohttp.ClientResponseError:
    return aiohttp.ClientResponseError(
        request_info=MagicMock(), history=(), status=status, message="err"
    )


@pytest.fixture
def no_firecrawl_key(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# 1. auto with FIRECRAWL_API_KEY -> firecrawl
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auto_with_firecrawl_key_uses_firecrawl():
    cfg = ContentCoreConfig(url_engine="auto")
    with patch.dict(
        "os.environ", {"FIRECRAWL_API_KEY": "test-key"}, clear=False
    ), patch(
        "content_core.processors.url.extract_url_firecrawl",
        new_callable=AsyncMock,
        return_value={"title": "T", "content": "C"},
    ) as mock_fc:
        result = await extract_from_url("https://example.com", cfg)
        mock_fc.assert_awaited_once_with("https://example.com", cfg)
        assert isinstance(result, ExtractionOutput)
        assert result.content == "C"
        assert result.title == "T"


# ---------------------------------------------------------------------------
# 2. auto without FIRECRAWL_API_KEY -> tries jina (success)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auto_without_key_uses_jina():
    cfg = ContentCoreConfig(url_engine="auto")
    with patch.dict(
        "os.environ", {}, clear=False
    ), patch(
        "content_core.processors.url.extract_url_firecrawl",
        new_callable=AsyncMock,
    ) as mock_fc, patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        return_value={"title": "Jina Title", "content": "Jina Content"},
    ) as mock_jina:
        # Remove FIRECRAWL_API_KEY if it exists
        env_patch = {}
        import os

        if "FIRECRAWL_API_KEY" in os.environ:
            env_patch["FIRECRAWL_API_KEY"] = ""
        with patch.dict("os.environ", env_patch, clear=False):
            # Ensure no FIRECRAWL_API_KEY
            with patch.dict("os.environ", {}, clear=False):
                os.environ.pop("FIRECRAWL_API_KEY", None)
                result = await extract_from_url("https://example.com", cfg)
                mock_jina.assert_awaited_once_with("https://example.com")
                mock_fc.assert_not_awaited()
                assert result.content == "Jina Content"


# ---------------------------------------------------------------------------
# 3. firecrawl engine -> uses firecrawl directly
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_firecrawl_engine():
    cfg = ContentCoreConfig(url_engine="firecrawl")
    with patch(
        "content_core.processors.url.extract_url_firecrawl",
        new_callable=AsyncMock,
        return_value={"title": "FC", "content": "FC Content"},
    ) as mock_fc:
        result = await extract_from_url("https://example.com", cfg)
        mock_fc.assert_awaited_once_with("https://example.com", cfg)
        assert result.content == "FC Content"


# ---------------------------------------------------------------------------
# 4. simple engine -> uses bs4 directly
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_simple_engine():
    cfg = ContentCoreConfig(url_engine="simple")
    with patch(
        "content_core.processors.url.extract_url_bs4",
        new_callable=AsyncMock,
        return_value={"title": "BS4", "content": "BS4 Content"},
    ) as mock_bs4:
        result = await extract_from_url("https://example.com", cfg)
        mock_bs4.assert_awaited_once_with("https://example.com")
        assert result.content == "BS4 Content"


# ---------------------------------------------------------------------------
# 5. jina engine -> uses jina directly
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_jina_engine():
    cfg = ContentCoreConfig(url_engine="jina")
    with patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        return_value={"title": "Jina", "content": "Jina Content"},
    ) as mock_jina:
        result = await extract_from_url("https://example.com", cfg)
        mock_jina.assert_awaited_once_with("https://example.com")
        assert result.content == "Jina Content"


# ---------------------------------------------------------------------------
# 6. firecrawl passes config (proxy + wait_for) through
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_firecrawl_receives_config_with_proxy_and_wait():
    cfg = ContentCoreConfig(
        url_engine="firecrawl",
        firecrawl_proxy="stealth",
        firecrawl_wait_for=5000,
    )
    with patch(
        "content_core.processors.url.extract_url_firecrawl",
        new_callable=AsyncMock,
        return_value={"title": "T", "content": "C"},
    ) as mock_fc:
        await extract_from_url("https://example.com", cfg)
        # Config is passed through so firecrawl can read proxy/wait_for
        passed_config = mock_fc.call_args[0][1]
        assert passed_config.firecrawl_proxy == "stealth"
        assert passed_config.firecrawl_wait_for == 5000


# ---------------------------------------------------------------------------
# 7. firecrawl default config has proxy=auto and wait_for=3000
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_firecrawl_default_proxy_and_wait():
    cfg = ContentCoreConfig(url_engine="firecrawl")
    assert cfg.firecrawl_proxy == "auto"
    assert cfg.firecrawl_wait_for == 3000


# ---------------------------------------------------------------------------
# 8. Failures raise typed errors; only `auto` falls through the chain
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unknown_engine_error_propagates():
    """An unknown engine is rejected before extraction, never swallowed.

    Literal validation on the config field makes this unreachable through
    normal config, so the bad value is assigned directly — mimicking a
    caller that bypasses the model.
    """
    cfg = ContentCoreConfig(url_engine="auto")
    cfg.url_engine = "jinaa"
    with pytest.raises(ConfigurationError) as exc:
        await extract_from_url("https://example.com", cfg)
    message = str(exc.value)
    assert "jinaa" in message
    for valid in ("auto", "simple", "firecrawl", "jina", "crawl4ai"):
        assert valid in message


@pytest.mark.asyncio
async def test_named_engine_unexpected_failure_raises_external_service_error():
    cfg = ContentCoreConfig(url_engine="simple")
    with patch(
        "content_core.processors.url.extract_url_bs4",
        new_callable=AsyncMock,
        side_effect=ValueError("boom"),
    ):
        with pytest.raises(ExternalServiceError) as exc:
            await extract_from_url("https://example.com", cfg)
    assert isinstance(exc.value.__cause__, ValueError)


@pytest.mark.asyncio
async def test_configuration_error_propagates():
    cfg = ContentCoreConfig(url_engine="firecrawl")
    with patch(
        "content_core.processors.url.extract_url_firecrawl",
        new_callable=AsyncMock,
        side_effect=ConfigurationError("FIRECRAWL_API_KEY not set"),
    ):
        with pytest.raises(ConfigurationError):
            await extract_from_url("https://example.com", cfg)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        ConnectionError("boom"),
        aiohttp.ClientConnectionError("dns"),
        aiohttp.ServerTimeoutError("slow"),
        TimeoutError("slow"),
    ],
)
async def test_named_engine_network_failure_raises_network_error(error):
    cfg = ContentCoreConfig(url_engine="jina")
    with patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        side_effect=error,
    ):
        with pytest.raises(NetworkError) as exc:
            await extract_from_url("https://example.com", cfg)
    assert exc.value.__cause__ is error


@pytest.mark.asyncio
async def test_named_api_engine_http_error_raises_external_service_error():
    cfg = ContentCoreConfig(url_engine="jina")
    with patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        side_effect=_http_error(401),
    ):
        with pytest.raises(ExternalServiceError, match="401"):
            await extract_from_url("https://example.com", cfg)


@pytest.mark.asyncio
async def test_firecrawl_sdk_error_raises_external_service_error():
    cfg = ContentCoreConfig(url_engine="firecrawl")
    with patch(
        "content_core.processors.url.firecrawl._fetch_url_firecrawl",
        new_callable=AsyncMock,
        side_effect=Exception("Unauthorized: invalid token"),
    ):
        with pytest.raises(ExternalServiceError):
            await extract_from_url("https://example.com", cfg)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 410])
async def test_simple_engine_missing_page_raises_not_found(status):
    cfg = ContentCoreConfig(url_engine="simple")
    with patch(
        "content_core.processors.url.bs4._fetch_url_html",
        new_callable=AsyncMock,
        side_effect=_http_error(status),
    ):
        with pytest.raises(NotFoundError):
            await extract_from_url("https://example.com/gone", cfg)


@pytest.mark.asyncio
async def test_simple_engine_server_error_raises_external_service_error():
    cfg = ContentCoreConfig(url_engine="simple")
    with patch(
        "content_core.processors.url.bs4._fetch_url_html",
        new_callable=AsyncMock,
        side_effect=_http_error(503),
    ):
        with pytest.raises(ExternalServiceError):
            await extract_from_url("https://example.com", cfg)


@pytest.mark.asyncio
async def test_named_crawl4ai_not_installed_raises_configuration_error():
    cfg = ContentCoreConfig(url_engine="crawl4ai", crawl4ai_api_url=None)
    with patch.dict("sys.modules", {"crawl4ai": None}), patch.dict(
        "os.environ", {}, clear=False
    ) as env:
        env.pop("CRAWL4AI_API_URL", None)
        with pytest.raises(ConfigurationError, match="content-core\\[crawl4ai\\]"):
            await extract_from_url("https://example.com", cfg)


@pytest.mark.asyncio
async def test_empty_page_returns_empty_content():
    """A page with nothing to extract is not an error."""
    cfg = ContentCoreConfig(url_engine="jina")
    with patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        return_value={"content": ""},
    ):
        result = await extract_from_url("https://example.com", cfg)
    assert result.content == ""


@pytest.mark.asyncio
async def test_simple_engine_empty_page_returns_empty_content():
    """No placeholder text: an empty page is content=""."""
    cfg = ContentCoreConfig(url_engine="simple")
    with patch(
        "content_core.processors.url.bs4._fetch_url_html",
        new_callable=AsyncMock,
        return_value="<html><body></body></html>",
    ):
        result = await extract_from_url("https://example.com/empty", cfg)
    assert result.content == ""


@pytest.mark.asyncio
async def test_simple_engine_empty_content_tag_falls_back_to_page_text():
    """An empty <main> must not mask visible text elsewhere on the page."""
    cfg = ContentCoreConfig(url_engine="simple")
    html = "<html><body><main></main><p>Visible text</p></body></html>"
    with patch(
        "content_core.processors.url.bs4._fetch_url_html",
        new_callable=AsyncMock,
        return_value=html,
    ), patch(
        "content_core.processors.url.bs4.Document",
        side_effect=ValueError("readability failed"),
    ):
        result = await extract_from_url("https://example.com", cfg)
    assert "Visible text" in result.content


@pytest.mark.asyncio
async def test_extract_content_malformed_ipv6_url_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        await extract_content(url="http://[::1/page")


@pytest.mark.asyncio
async def test_malformed_url_raises_invalid_input():
    cfg = ContentCoreConfig(url_engine="simple")
    with patch(
        "content_core.processors.url.bs4._fetch_url_html",
        new_callable=AsyncMock,
        side_effect=aiohttp.InvalidURL("ftp//nope"),
    ):
        with pytest.raises(InvalidInputError):
            await extract_from_url("ftp//nope", cfg)


# ---------------------------------------------------------------------------
# 9. auto falls through the chain and raises only when every engine failed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_auto_falls_through_to_bs4(no_firecrawl_key):
    cfg = ContentCoreConfig(url_engine="auto")
    with patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        side_effect=_http_error(500),
    ) as jina, patch(
        "content_core.processors.url.extract_url_crawl4ai",
        new_callable=AsyncMock,
        side_effect=ConfigurationError("Crawl4AI is not installed"),
    ) as crawl, patch(
        "content_core.processors.url.extract_url_bs4",
        new_callable=AsyncMock,
        return_value={"title": "B", "content": "BS4 Content"},
    ) as bs4:
        result = await extract_from_url("https://example.com", cfg)
    jina.assert_awaited_once()
    crawl.assert_awaited_once()
    bs4.assert_awaited_once()
    assert result.content == "BS4 Content"


@pytest.mark.asyncio
async def test_auto_firecrawl_failure_falls_through_to_jina(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    cfg = ContentCoreConfig(url_engine="auto")
    with patch(
        "content_core.processors.url.extract_url_firecrawl",
        new_callable=AsyncMock,
        side_effect=Exception("rate limited"),
    ), patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        return_value={"title": "J", "content": "Jina Content"},
    ):
        result = await extract_from_url("https://example.com", cfg)
    assert result.content == "Jina Content"


@pytest.mark.asyncio
async def test_auto_raises_last_error_when_every_engine_fails(no_firecrawl_key):
    cfg = ContentCoreConfig(url_engine="auto")
    last = aiohttp.ClientConnectionError("dns")
    with patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        side_effect=_http_error(500),
    ), patch(
        "content_core.processors.url.extract_url_crawl4ai",
        new_callable=AsyncMock,
        side_effect=RuntimeError("no browser"),
    ), patch(
        "content_core.processors.url.extract_url_bs4",
        new_callable=AsyncMock,
        side_effect=last,
    ):
        with pytest.raises(NetworkError) as exc:
            await extract_from_url("https://example.com", cfg)
    assert exc.value.__cause__ is last


# ---------------------------------------------------------------------------
# 10. extract_content: an unreachable host raises, it does not return empty
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("engine", ["simple", "auto"])
async def test_extract_content_unreachable_host_raises_network_error(
    engine, no_firecrawl_key
):
    unreachable = aiohttp.ClientConnectionError("Cannot connect to host")
    cfg = ContentCoreConfig(url_engine=engine)
    with patch(
        "content_core.processors.url._fetch_url_mime_type",
        new_callable=AsyncMock,
        side_effect=unreachable,
    ), patch(
        "content_core.processors.url.jina._fetch_url_jina",
        new_callable=AsyncMock,
        side_effect=_http_error(502),
    ), patch(
        "content_core.processors.url.extract_url_crawl4ai",
        new_callable=AsyncMock,
        side_effect=ConfigurationError("Crawl4AI is not installed"),
    ), patch(
        "content_core.processors.url.bs4._fetch_url_html",
        new_callable=AsyncMock,
        side_effect=unreachable,
    ):
        with pytest.raises(NetworkError):
            await extract_content(url="https://unreachable.invalid/page", config=cfg)


# ---------------------------------------------------------------------------
# 11. crawl4ai: a failed crawl is returned by the library, not raised
# ---------------------------------------------------------------------------
def _fake_crawl4ai(result):
    """A stand-in ``crawl4ai`` module whose crawler returns ``result``."""
    crawler = MagicMock()
    crawler.arun = AsyncMock(return_value=result)
    crawler.__aenter__ = AsyncMock(return_value=crawler)
    crawler.__aexit__ = AsyncMock(return_value=False)
    module = MagicMock()
    module.AsyncWebCrawler = MagicMock(return_value=crawler)
    return module


@pytest.fixture
def crawl4ai_local(monkeypatch):
    monkeypatch.delenv("CRAWL4AI_API_URL", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("HTTPS_PROXY", raising=False)


@pytest.mark.asyncio
async def test_named_crawl4ai_failed_crawl_raises_external_service_error(crawl4ai_local):
    failed = MagicMock(success=False, markdown=None, error_message="net::ERR_ABORTED")
    cfg = ContentCoreConfig(url_engine="crawl4ai", crawl4ai_api_url=None)
    with patch.dict("sys.modules", {"crawl4ai": _fake_crawl4ai(failed)}):
        with pytest.raises(ExternalServiceError, match="ERR_ABORTED"):
            await extract_from_url("https://example.com", cfg)


@pytest.mark.asyncio
async def test_auto_falls_through_failed_crawl4ai_crawl_to_simple(
    crawl4ai_local, no_firecrawl_key
):
    failed = MagicMock(success=False, markdown=None, error_message="net::ERR_ABORTED")
    cfg = ContentCoreConfig(url_engine="auto", crawl4ai_api_url=None)
    fake = _fake_crawl4ai(failed)
    with patch.dict("sys.modules", {"crawl4ai": fake}), patch(
        "content_core.processors.url.extract_url_jina",
        new_callable=AsyncMock,
        side_effect=_http_error(500),
    ), patch(
        "content_core.processors.url.extract_url_bs4",
        new_callable=AsyncMock,
        return_value={"title": "T", "content": "from simple"},
    ):
        result = await extract_from_url("https://example.com", cfg)
    fake.AsyncWebCrawler.return_value.arun.assert_awaited()
    assert result.content == "from simple"


@pytest.mark.asyncio
async def test_named_crawl4ai_successful_crawl_returns_markdown(crawl4ai_local):
    ok = MagicMock(success=True, markdown="# Hello", metadata={"title": "Page"})
    cfg = ContentCoreConfig(url_engine="crawl4ai", crawl4ai_api_url=None)
    with patch.dict("sys.modules", {"crawl4ai": _fake_crawl4ai(ok)}):
        result = await extract_from_url("https://example.com", cfg)
    assert result.content == "# Hello"
    assert result.title == "Page"


@pytest.mark.asyncio
async def test_named_crawl4ai_markdown_result_object_uses_raw_markdown(crawl4ai_local):
    """Older crawl4ai returns a MarkdownGenerationResult, not a str."""
    md = MagicMock(raw_markdown="# Raw")
    ok = MagicMock(success=True, markdown=md, metadata={"title": "Page"})
    cfg = ContentCoreConfig(url_engine="crawl4ai", crawl4ai_api_url=None)
    with patch.dict("sys.modules", {"crawl4ai": _fake_crawl4ai(ok)}):
        result = await extract_from_url("https://example.com", cfg)
    assert result.content == "# Raw"
