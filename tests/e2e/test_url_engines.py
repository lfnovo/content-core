"""E2E tests for URL extraction engines — require network access."""
import os
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.e2e
from content_core.config import ContentCoreConfig
from content_core.extraction import extract_content


@pytest.mark.asyncio
async def test_extract_content_from_url():
    """Tests content extraction from a URL using bs4/simple engine."""
    result = await extract_content(
        url="https://www.supernovalabs.com",
        config=ContentCoreConfig(url_engine="simple"),
    )

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    assert "Supernova Labs" in result.title
    assert "AI Consulting" in result.title


@pytest.mark.asyncio
async def test_extract_content_from_url_firecrawl():
    """Tests content extraction from a URL using Firecrawl engine."""
    try:
        import firecrawl  # noqa: F401
    except ImportError:
        pytest.skip("Firecrawl not installed")

    result = await extract_content(
        url="https://www.supernovalabs.com",
        config=ContentCoreConfig(url_engine="firecrawl"),
    )

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    assert "Supernova Labs" in result.title
    assert "AI Consulting" in result.title
    assert len(result.content) > 100
    assert "AI" in result.content


@pytest.mark.asyncio
async def test_extract_content_from_url_jina():
    """Tests content extraction from a URL using Jina engine."""
    result = await extract_content(
        url="https://www.supernovalabs.com",
        config=ContentCoreConfig(url_engine="jina"),
    )

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    assert "Supernova Labs" in result.title
    assert len(result.content) > 100
    assert "AI" in result.content


@pytest.mark.asyncio
async def test_extract_content_from_url_crawl4ai():
    """Tests content extraction from a URL using Crawl4AI."""
    pytest.importorskip("crawl4ai", reason="Crawl4AI not installed")

    result = await extract_content(
        url="https://www.supernovalabs.com",
        config=ContentCoreConfig(url_engine="crawl4ai"),
    )

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    assert "Supernova Labs" in result.title
    assert "AI Consulting" in result.title
    assert len(result.content) > 100
    assert "AI" in result.content


@pytest.mark.asyncio
async def test_auto_mode_fallback_to_crawl4ai():
    """Tests that auto mode correctly falls back to Crawl4AI when Jina fails.

    This test verifies the fallback chain:
    1. Auto mode tries Jina first (when no FIRECRAWL_API_KEY)
    2. When Jina raises an exception, it should try Crawl4AI
    3. When Crawl4AI succeeds, content should be returned
    """
    pytest.importorskip(
        "crawl4ai",
        reason="Crawl4AI not installed - auto mode fallback test requires Crawl4AI",
    )

    # Temporarily ensure FIRECRAWL_API_KEY is not set (so auto mode tries Jina first)
    original_firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
    if original_firecrawl_key:
        del os.environ["FIRECRAWL_API_KEY"]

    try:
        # Mock extract_url_jina to raise an exception (simulating Jina failure)
        with patch("content_core.processors.url.extract_url_jina") as mock_jina:
            mock_jina.side_effect = Exception("Jina API error (mocked)")

            test_url = "https://www.supernovalabs.com"

            result = await extract_content(
                url=test_url,
                config=ContentCoreConfig(url_engine="auto"),
            )

            assert result is not None
            assert hasattr(result, "source_type")
            assert result.source_type == "url"

            assert len(result.content) > 100
            assert "AI" in result.content or "Supernova" in result.title

            mock_jina.assert_called_once_with(test_url)

    finally:
        if original_firecrawl_key:
            os.environ["FIRECRAWL_API_KEY"] = original_firecrawl_key
