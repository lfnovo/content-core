import os

import aiohttp

from content_core.common import ProcessSourceState
from content_core.common.retry import retry_url_network
from content_core.config import (
    DEFAULT_FIRECRAWL_API_URL,
    get_firecrawl_api_url,
    get_url_engine,
)
from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.models_v2 import ExtractionOutput
from content_core.processors.document.docling import DOCLING_SUPPORTED
from content_core.processors.document import SUPPORTED_OFFICE_TYPES
from content_core.processors.pdf import SUPPORTED_FITZ_TYPES

# Import engine functions from sub-modules
from content_core.processors.url.bs4 import _fetch_url_html, extract_url_bs4
from content_core.processors.url.jina import _fetch_url_jina, extract_url_jina
from content_core.processors.url.firecrawl import (
    _fetch_url_firecrawl,
    extract_url_firecrawl,
)
from content_core.processors.url.crawl4ai import (
    _fetch_url_crawl4ai,
    extract_url_crawl4ai,
)


@retry_url_network()
async def _fetch_url_mime_type(url: str) -> str:
    """Internal function to fetch URL MIME type - wrapped with retry logic."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.head(url, timeout=10, allow_redirects=True) as resp:
            mime = resp.headers.get("content-type", "").split(";", 1)[0]
            logger.debug(f"MIME type for {url}: {mime}")
            return mime


async def url_provider(state: ProcessSourceState):
    """
    Identify the provider with retry logic for network requests.
    """
    return_dict = {}
    url = state.url
    if url:
        if "youtube.com" in url or "youtu.be" in url:
            return_dict["identified_type"] = "youtube"
        else:
            # remote URL: check content-type to catch PDFs
            try:
                mime = await _fetch_url_mime_type(url)
            except Exception as e:
                logger.warning(f"HEAD check failed for {url} after retries: {e}")
                mime = "article"
            if (
                mime in DOCLING_SUPPORTED
                or mime in SUPPORTED_FITZ_TYPES
                or mime in SUPPORTED_OFFICE_TYPES
            ):
                logger.debug(f"Identified type for {url}: {mime}")
                return_dict["identified_type"] = mime
            else:
                logger.debug(f"Identified type for {url}: article")
                return_dict["identified_type"] = "article"
    return return_dict


async def extract_url(state: ProcessSourceState):
    """
    Extract content from a URL using the url_engine specified in the state.
    Supported engines: 'auto', 'simple', 'firecrawl', 'jina', 'crawl4ai'.

    Proxy is configured via standard HTTP_PROXY/HTTPS_PROXY environment variables.
    """
    assert state.url, "No URL provided"
    url = state.url
    # Use environment-aware engine selection
    engine = state.url_engine or get_url_engine()
    try:
        if engine == "auto":
            if os.environ.get("FIRECRAWL_API_KEY"):
                logger.debug(
                    "Engine 'auto' selected: using Firecrawl (FIRECRAWL_API_KEY detected)"
                )
                return await extract_url_firecrawl(url)
            else:
                try:
                    logger.debug("Trying to use Jina to extract URL")
                    return await extract_url_jina(url)
                except Exception as e:
                    logger.error(f"Jina extraction error for URL: {url}: {e}")
                    # Try Crawl4AI before falling back to BeautifulSoup
                    logger.debug("Trying to use Crawl4AI to extract URL")
                    result = await extract_url_crawl4ai(url)
                    if result is not None:
                        return result
                    logger.debug(
                        "Crawl4AI failed or not installed, falling back to BeautifulSoup"
                    )
                    return await extract_url_bs4(url)
        elif engine == "simple":
            return await extract_url_bs4(url)
        elif engine == "firecrawl":
            return await extract_url_firecrawl(url)
        elif engine == "jina":
            return await extract_url_jina(url)
        elif engine == "crawl4ai":
            return await extract_url_crawl4ai(url)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    except Exception as e:
        logger.error(f"URL extraction failed for URL: {url}")
        logger.exception(e)
        return None


async def detect_remote_mime(url: str) -> str:
    """Detect MIME type of a remote URL via HEAD request."""
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    try:
        mime = await _fetch_url_mime_type(url)
    except Exception as e:
        logger.warning(f"HEAD check failed for {url} after retries: {e}")
        return "article"

    if (
        mime in DOCLING_SUPPORTED
        or mime in SUPPORTED_FITZ_TYPES
        or mime in SUPPORTED_OFFICE_TYPES
    ):
        return mime
    return "article"


async def _extract_url_with_engine(url: str, engine: str, firecrawl_api_url: str) -> dict:
    """Run the URL extraction with a specific engine and fallback chain."""
    if engine == "auto":
        if os.environ.get("FIRECRAWL_API_KEY"):
            logger.debug(
                "Engine 'auto' selected: using Firecrawl (FIRECRAWL_API_KEY detected)"
            )
            return await extract_url_firecrawl(url)
        else:
            try:
                logger.debug("Trying to use Jina to extract URL")
                return await extract_url_jina(url)
            except Exception as e:
                logger.error(f"Jina extraction error for URL: {url}: {e}")
                logger.debug("Trying to use Crawl4AI to extract URL")
                result = await extract_url_crawl4ai(url)
                if result is not None:
                    return result
                logger.debug(
                    "Crawl4AI failed or not installed, falling back to BeautifulSoup"
                )
                return await extract_url_bs4(url)
    elif engine == "simple":
        return await extract_url_bs4(url)
    elif engine == "firecrawl":
        return await extract_url_firecrawl(url)
    elif engine == "jina":
        return await extract_url_jina(url)
    elif engine == "crawl4ai":
        return await extract_url_crawl4ai(url)
    else:
        raise ValueError(f"Unknown engine: {engine}")


async def extract_from_url(url: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content from a URL using configured engine with fallback chain."""
    try:
        result = await _extract_url_with_engine(
            url, config.url_engine, config.firecrawl_api_url
        )
        if result is None:
            return ExtractionOutput(
                content="",
                source_type="url",
                identified_type="article",
            )
        return ExtractionOutput(
            content=result.get("content", ""),
            title=result.get("title", ""),
            source_type="url",
            identified_type="article",
        )
    except Exception as e:
        logger.error(f"URL extraction failed for URL: {url}")
        logger.exception(e)
        return ExtractionOutput(
            content="",
            source_type="url",
            identified_type="article",
        )


__all__ = [
    "_fetch_url_mime_type",
    "_fetch_url_html",
    "_fetch_url_jina",
    "_fetch_url_firecrawl",
    "_fetch_url_crawl4ai",
    "url_provider",
    "extract_url",
    "extract_url_bs4",
    "extract_url_jina",
    "extract_url_firecrawl",
    "extract_url_crawl4ai",
    "detect_remote_mime",
    "_extract_url_with_engine",
    "extract_from_url",
]
