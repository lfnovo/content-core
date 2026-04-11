"""Tests for URL engine selection logic in extract_from_url."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.common.state import ExtractionOutput
from content_core.processors.url import extract_from_url


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
        mock_fc.assert_awaited_once_with("https://example.com")
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
        mock_fc.assert_awaited_once_with("https://example.com")
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
