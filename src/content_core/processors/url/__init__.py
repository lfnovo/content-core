import os

import aiohttp

from content_core.common.retry import retry_url_network
from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput
from content_core.processors.document.docling import DOCLING_SUPPORTED
from content_core.processors.document import SUPPORTED_OFFICE_TYPES
from content_core.processors.document.pdf import SUPPORTED_PDF_TYPES
from content_core.processors.document.epub import SUPPORTED_EPUB_TYPES

# Import engine functions from sub-modules
from content_core.processors.url.bs4 import _fetch_url_html, extract_url_bs4
from content_core.processors.url.jina import _fetch_url_jina, extract_url_jina
from content_core.processors.url.firecrawl import (
    _fetch_url_firecrawl,
    extract_url_firecrawl,
)
from content_core.processors.url.crawl4ai import extract_url_crawl4ai


@retry_url_network()
async def _fetch_url_mime_type(url: str) -> str:
    """Internal function to fetch URL MIME type - wrapped with retry logic."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.head(url, timeout=10, allow_redirects=True) as resp:
            mime = resp.headers.get("content-type", "").split(";", 1)[0]
            logger.debug(f"MIME type for {url}: {mime}")
            return mime


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
        or mime in SUPPORTED_PDF_TYPES
        or mime in SUPPORTED_EPUB_TYPES
        or mime in SUPPORTED_OFFICE_TYPES
    ):
        return mime
    return "article"


async def _extract_url_with_engine(url: str, engine: str, config: ContentCoreConfig) -> dict:
    """Run the URL extraction with a specific engine and fallback chain."""
    if engine == "auto":
        if os.environ.get("FIRECRAWL_API_KEY"):
            logger.debug(
                "Engine 'auto' selected: using Firecrawl (FIRECRAWL_API_KEY detected)"
            )
            try:
                result = await extract_url_firecrawl(url, config)
                if result is not None:
                    return result
            except Exception as e:
                logger.error(f"Firecrawl extraction error for URL: {url}: {e}")
            logger.debug("Firecrawl failed, falling through to jina→crawl4ai→bs4 chain")

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
        return await extract_url_firecrawl(url, config)
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
            url, config.url_engine, config
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


from content_core.processors.url.reddit import (
    extract_reddit,
    is_reddit_post,
)
from content_core.processors.url.youtube import (
    extract_youtube,
    get_best_transcript,
    get_video_title,
    extract_transcript_pytubefix,
)

__all__ = [
    "_fetch_url_mime_type",
    "_fetch_url_html",
    "_fetch_url_jina",
    "_fetch_url_firecrawl",
    "extract_url_bs4",
    "extract_url_jina",
    "extract_url_firecrawl",
    "extract_url_crawl4ai",
    "detect_remote_mime",
    "_extract_url_with_engine",
    "extract_from_url",
    "extract_reddit",
    "is_reddit_post",
    "extract_youtube",
    "get_best_transcript",
    "get_video_title",
    "extract_transcript_pytubefix",
]
