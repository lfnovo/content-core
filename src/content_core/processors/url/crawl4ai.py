import os

from content_core.common.retry import retry_url_api
from content_core.logging import logger


@retry_url_api()
async def _fetch_url_crawl4ai(url: str) -> dict:
    """Internal function to fetch URL content via Crawl4AI - wrapped with retry logic."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, ProxyConfig
    except ImportError:
        raise ImportError(
            "Crawl4AI is not installed. Install it with: pip install content-core[crawl4ai]"
        )

    # Crawl4AI doesn't read env vars automatically, so we bridge HTTP_PROXY to ProxyConfig
    proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")

    # Configure proxy if available
    run_config = None
    if proxy_url:
        try:
            run_config = CrawlerRunConfig(
                proxy_config=ProxyConfig.from_string(proxy_url)
            )
            logger.debug(f"Crawl4AI using proxy from environment")
        except Exception as e:
            logger.warning(f"Failed to configure proxy for Crawl4AI: {e}")

    async with AsyncWebCrawler() as crawler:
        if run_config:
            result = await crawler.arun(url=url, config=run_config)
        else:
            result = await crawler.arun(url=url)

        # Extract title from metadata if available
        title = ""
        if hasattr(result, "metadata") and result.metadata:
            title = result.metadata.get("title", "")

        # Get markdown content
        content = result.markdown if hasattr(result, "markdown") else ""

        return {
            "title": title or "No title found",
            "content": content,
        }


async def extract_url_crawl4ai(url: str) -> dict | None:
    """
    Get the content of a URL using Crawl4AI (local browser automation).
    Returns {"title": ..., "content": ...} or None on failure.
    Includes retry logic for transient failures.

    Args:
        url (str): The URL to extract content from.
    """
    try:
        return await _fetch_url_crawl4ai(url)
    except Exception:
        return None
