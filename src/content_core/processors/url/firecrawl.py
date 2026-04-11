import os

from content_core.common.retry import retry_url_api
from content_core.config import (
    DEFAULT_FIRECRAWL_API_URL,
    get_firecrawl_api_url,
)
from content_core.logging import logger


@retry_url_api()
async def _fetch_url_firecrawl(url: str) -> dict:
    """Internal function to fetch URL content via Firecrawl - wrapped with retry logic."""
    from firecrawl import AsyncFirecrawlApp

    # Note: firecrawl-py does not support client-side proxy configuration
    # Proxy must be configured on the Firecrawl server side

    # Get custom API URL for self-hosted instances
    api_url = get_firecrawl_api_url()
    if api_url != DEFAULT_FIRECRAWL_API_URL:
        logger.debug(f"Using custom Firecrawl API URL: {api_url}")

    app = AsyncFirecrawlApp(
        api_key=os.environ.get("FIRECRAWL_API_KEY"),
        api_url=api_url,
    )
    scrape_result = await app.scrape(url, formats=["markdown", "html"])
    return {
        "title": scrape_result.metadata.title or "",
        "content": scrape_result.markdown or "",
    }


async def extract_url_firecrawl(url: str) -> dict | None:
    """
    Get the content of a URL using Firecrawl.
    Returns {"title": ..., "content": ...} or None on failure.
    Includes retry logic for transient API failures.

    Note: Firecrawl does not support client-side proxy configuration.
    """
    try:
        return await _fetch_url_firecrawl(url)
    except Exception as e:
        logger.error(f"Firecrawl extraction failed for {url} after retries: {e}")
        return None
