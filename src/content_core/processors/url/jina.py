import os

import aiohttp

from content_core.common.retry import retry_url_api
from content_core.logging import logger


@retry_url_api()
async def _fetch_url_jina(url: str, headers: dict) -> str:
    """Internal function to fetch URL content via Jina - wrapped with retry logic."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(
            f"https://r.jina.ai/{url}", headers=headers
        ) as response:
            # Raise ClientResponseError so retry logic can inspect status code
            # (5xx and 429 will be retried, 4xx will not)
            response.raise_for_status()
            return await response.text()


async def extract_url_jina(url: str) -> dict:
    """
    Get the content of a URL using Jina. Uses Bearer token if JINA_API_KEY is set.
    Includes retry logic for transient API failures.

    Args:
        url (str): The URL to extract content from.
    """
    headers = {}
    api_key = os.environ.get("JINA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        text = await _fetch_url_jina(url, headers)
        if text.startswith("Title:") and "\n" in text:
            title_end = text.index("\n")
            title = text[6:title_end].strip()
            content = text[title_end + 1 :].strip()
            logger.debug(
                f"Processed url: {url}, found title: {title}, content: {content[:100]}..."
            )
            return {"title": title, "content": content}
        else:
            logger.debug(
                f"Processed url: {url}, does not have Title prefix, returning full content: {text[:100]}..."
            )
            return {"content": text}
    except Exception as e:
        logger.error(f"Jina extraction failed for {url} after retries: {e}")
        raise
