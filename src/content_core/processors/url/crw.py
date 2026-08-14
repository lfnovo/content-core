import os

import aiohttp

from content_core.common.retry import retry_url_api
from content_core.config import (
    ContentCoreConfig,
    DEFAULT_CRW_API_URL,
    get_default_config,
)
from content_core.logging import logger


@retry_url_api()
async def _fetch_url_crw(url: str, config: ContentCoreConfig) -> dict:
    """Internal function to fetch URL content via CRW - wrapped with retry logic."""
    api_url = os.environ.get("CRW_API_URL") or config.crw_api_url
    if api_url != DEFAULT_CRW_API_URL:
        logger.debug(f"Using custom CRW API URL: {api_url}")

    payload: dict = {"url": url, "formats": ["markdown"], "onlyMainContent": True}
    if config.crw_render_js:
        payload["renderJs"] = True
    if config.crw_wait_for > 0:
        payload["waitFor"] = config.crw_wait_for

    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("CRW_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.post(
            f"{api_url.rstrip('/')}/v1/scrape",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as response:
            response.raise_for_status()
            body = await response.json()

    data = body.get("data") or {}
    return {
        "title": (data.get("metadata") or {}).get("title", ""),
        "content": data.get("markdown", ""),
    }


async def extract_url_crw(url: str, config: ContentCoreConfig | None = None) -> dict | None:
    """
    Get the content of a URL using CRW.
    Returns {"title": ..., "content": ...} or None on failure.
    Includes retry logic for transient API failures.
    """
    cfg = config or get_default_config()
    try:
        return await _fetch_url_crw(url, cfg)
    except Exception as e:
        logger.error(f"CRW extraction failed for {url} after retries: {e}")
        return None
