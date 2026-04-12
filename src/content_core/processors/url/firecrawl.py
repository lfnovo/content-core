import os

from content_core.common.retry import retry_url_api
from content_core.config import (
    ContentCoreConfig,
    DEFAULT_FIRECRAWL_API_URL,
    get_default_config,
)
from content_core.logging import logger


@retry_url_api()
async def _fetch_url_firecrawl(url: str, config: ContentCoreConfig) -> dict:
    """Internal function to fetch URL content via Firecrawl - wrapped with retry logic."""
    from firecrawl import AsyncFirecrawlApp

    api_url = os.environ.get("FIRECRAWL_API_URL") or config.firecrawl_api_url
    if api_url != DEFAULT_FIRECRAWL_API_URL:
        logger.debug(f"Using custom Firecrawl API URL: {api_url}")

    app = AsyncFirecrawlApp(
        api_key=os.environ.get("FIRECRAWL_API_KEY"),
        api_url=api_url,
    )

    scrape_kwargs = {"formats": ["markdown", "html"]}

    if config.firecrawl_proxy:
        scrape_kwargs["proxy"] = config.firecrawl_proxy
    if config.firecrawl_wait_for > 0:
        scrape_kwargs["wait_for"] = config.firecrawl_wait_for

    scrape_result = await app.scrape(url, **scrape_kwargs)
    return {
        "title": scrape_result.metadata.title or "",
        "content": scrape_result.markdown or "",
    }


async def extract_url_firecrawl(url: str, config: ContentCoreConfig | None = None) -> dict | None:
    """
    Get the content of a URL using Firecrawl.
    Returns {"title": ..., "content": ...} or None on failure.
    Includes retry logic for transient API failures.
    """
    cfg = config or get_default_config()
    try:
        return await _fetch_url_firecrawl(url, cfg)
    except Exception as e:
        logger.error(f"Firecrawl extraction failed for {url} after retries: {e}")
        return None
