import os
import uuid

import aiohttp

from content_core.common.retry import retry_url_api
from content_core.config import ContentCoreConfig, get_default_config
from content_core.logging import logger


# Pages SpecStream processed: "empty" is a page with no main text, returned as content="".
_READ_STATUSES = frozenset({"ok", "empty"})


@retry_url_api()
async def _fetch_url_specstream(url: str, config: ContentCoreConfig, idempotency_key: str) -> dict:
    """Internal function to fetch URL content via SpecStream - wrapped with retry logic.

    Every retry sends the same ``Idempotency-Key``, so a call whose reply was lost is charged
    once: SpecStream replays the reply it already paid for instead of reading the page again.
    """
    api_url = os.environ.get("SPECSTREAM_API_URL") or config.specstream_api_url
    api_key = os.environ.get("SPECSTREAM_API_KEY") or config.specstream_api_key

    headers = {"Idempotency-Key": idempotency_key}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with aiohttp.ClientSession(trust_env=True, headers=headers) as session:
        async with session.post(
            f"{api_url.rstrip('/')}/v1/extract",
            json={"urls": [url], "format": "markdown"},
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    results = (data.get("data") or {}).get("results") or []
    if not results:
        raise ValueError("No results returned from SpecStream Extract API")

    result = results[0]
    if result.get("status") not in _READ_STATUSES:
        raise RuntimeError(
            f"SpecStream could not read {url}: {result.get('status') or 'unknown status'}"
        )
    return {
        "title": result.get("title") or "",
        "content": result.get("text") or "",
    }


async def extract_url_specstream(url: str, config: ContentCoreConfig | None = None) -> dict:
    """
    Get the content of a URL using SpecStream.
    Returns {"title": ..., "content": ...}; raises on failure.
    Includes retry logic for transient API failures.
    """
    cfg = config or get_default_config()
    try:
        return await _fetch_url_specstream(url, cfg, uuid.uuid4().hex)
    except Exception as e:
        logger.error(f"SpecStream extraction failed for {url} after retries: {e}")
        raise
