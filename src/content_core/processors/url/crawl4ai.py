import os
from typing import Optional

import aiohttp

from content_core.common.retry import retry_url_api
from content_core.config import ContentCoreConfig, get_default_config
from content_core.logging import logger


@retry_url_api()
async def _fetch_url_crawl4ai_docker(
    url: str, api_url: str, api_token: Optional[str] = None
) -> dict:
    """Fetch URL content via Crawl4AI Docker API.

    Crawl4AI >= 0.9.0 requires a bearer token for external connections by
    default; when ``api_token`` is set it is sent as ``Authorization: Bearer``.
    """
    headers = {"Authorization": f"Bearer {api_token}"} if api_token else None
    async with aiohttp.ClientSession(trust_env=True, headers=headers) as session:
        async with session.post(
            f"{api_url.rstrip('/')}/crawl",
            json={"urls": [url], "priority": 10},
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            response.raise_for_status()
            data = await response.json()

    if "results" not in data or not data["results"]:
        raise ValueError("No results returned from Crawl4AI Docker API")

    result = data["results"][0]
    title = result.get("metadata", {}).get("title", "")

    # Docker API: markdown can be a dict with raw_markdown or a string
    markdown_data = result.get("markdown", {})
    if isinstance(markdown_data, dict):
        content = markdown_data.get("raw_markdown", "")
    else:
        content = str(markdown_data) if markdown_data else ""

    return {
        "title": title or "No title found",
        "content": content,
    }


@retry_url_api()
async def _fetch_url_crawl4ai_local(url: str) -> dict:
    """Fetch URL content via local Crawl4AI browser automation."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, ProxyConfig
    except ImportError:
        raise ImportError(
            "Crawl4AI is not installed. Install it with: pip install content-core[crawl4ai]"
        )

    # Bridge HTTP_PROXY to Crawl4AI's ProxyConfig
    proxy_url = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")

    run_config = None
    if proxy_url:
        try:
            run_config = CrawlerRunConfig(
                proxy_config=ProxyConfig.from_string(proxy_url)
            )
            logger.debug("Crawl4AI using proxy from environment")
        except Exception as e:
            logger.warning(f"Failed to configure proxy for Crawl4AI: {e}")

    async with AsyncWebCrawler() as crawler:
        if run_config:
            result = await crawler.arun(url=url, config=run_config)
        else:
            result = await crawler.arun(url=url)

        title = ""
        if hasattr(result, "metadata") and result.metadata:
            title = result.metadata.get("title", "")

        content = result.markdown if hasattr(result, "markdown") else ""

        return {
            "title": title or "No title found",
            "content": content,
        }


async def extract_url_crawl4ai(url: str, config: Optional[ContentCoreConfig] = None) -> dict | None:
    """Get the content of a URL using Crawl4AI.

    Automatically selects Docker API mode (when CRAWL4AI_API_URL is set)
    or local browser automation mode.

    Returns {"title": ..., "content": ...} or None on failure.
    """
    cfg = config or get_default_config()
    api_url = os.environ.get("CRAWL4AI_API_URL") or cfg.crawl4ai_api_url
    api_token = os.environ.get("CRAWL4AI_API_TOKEN") or cfg.crawl4ai_api_token

    try:
        if api_url:
            logger.debug(f"Using Crawl4AI Docker API at: {api_url}")
            return await _fetch_url_crawl4ai_docker(url, api_url, api_token)
        else:
            logger.debug("Using Crawl4AI local browser automation")
            return await _fetch_url_crawl4ai_local(url)
    except Exception as e:
        logger.error(f"Crawl4AI extraction failed for {url}: {e}")
        return None
