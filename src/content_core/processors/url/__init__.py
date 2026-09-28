import asyncio
import os
from typing import get_args

import aiohttp

from content_core.common.exceptions import (
    ConfigurationError,
    ContentCoreError,
    ExternalServiceError,
    InvalidInputError,
    NetworkError,
    NotFoundError,
)
from content_core.common.retry import retry_url_network
from content_core.common.types import UrlEngine
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


try:
    import httpx

    _HTTPX_TRANSPORT_ERRORS: tuple = (httpx.TransportError,)
except ImportError:  # pragma: no cover - httpx ships with firecrawl-py
    _HTTPX_TRANSPORT_ERRORS = ()

# Connection, timeout and DNS failures: the remote end was never reached.
# (aiohttp's connector errors and socket.gaierror are OSError subclasses.)
_NETWORK_ERRORS = (
    aiohttp.ClientConnectionError,
    asyncio.TimeoutError,
    TimeoutError,
    OSError,
) + _HTTPX_TRANSPORT_ERRORS


def to_typed_url_error(exc: Exception, url: str, service: str) -> ContentCoreError:
    """Map an untyped failure fetching ``url`` through ``service`` to the taxonomy.

    ``service`` names what was being talked to: an engine name ("jina",
    "firecrawl", "crawl4ai", "simple") or "download". HTTP 404/410 from the
    target itself ("simple" and "download" fetch the URL directly) is
    ``NotFoundError``; any other HTTP error or API failure is
    ``ExternalServiceError``; connection/timeout/DNS is ``NetworkError``; a
    malformed URL is ``InvalidInputError``.
    """
    if isinstance(exc, aiohttp.InvalidURL):
        return InvalidInputError(f"Invalid URL {url}: {exc}")
    if isinstance(exc, aiohttp.ClientResponseError):
        if service in ("simple", "download") and exc.status in (404, 410):
            return NotFoundError(f"{url} returned HTTP {exc.status}")
        return ExternalServiceError(
            f"{service} failed for {url}: HTTP {exc.status} {exc.message}"
        )
    if isinstance(exc, _NETWORK_ERRORS):
        return NetworkError(f"{service} could not reach {url}: {exc!r}")
    return ExternalServiceError(f"{service} failed for {url}: {exc!r}")


async def _run_engine(url: str, engine: str, config: ContentCoreConfig) -> dict:
    """Run one named engine; any failure comes out typed."""
    try:
        if engine == "simple":
            return await extract_url_bs4(url)
        elif engine == "firecrawl":
            return await extract_url_firecrawl(url, config)
        elif engine == "jina":
            return await extract_url_jina(url)
        elif engine == "crawl4ai":
            return await extract_url_crawl4ai(url)
    except ContentCoreError:
        raise
    except Exception as e:
        raise to_typed_url_error(e, url, engine) from e
    raise ConfigurationError(f"Unknown URL engine: {engine!r}")


async def _extract_url_with_engine(url: str, engine: str, config: ContentCoreConfig) -> dict:
    """Run the URL extraction with a specific engine, or the ``auto`` chain.

    A named engine is honored or raises. ``auto`` tries each engine in turn
    (firecrawl when FIRECRAWL_API_KEY is set, then jina -> crawl4ai -> simple)
    and raises the last engine's error only if every one of them failed.
    """
    if engine != "auto":
        return await _run_engine(url, engine, config)

    chain = ["jina", "crawl4ai", "simple"]
    if os.environ.get("FIRECRAWL_API_KEY"):
        logger.debug(
            "Engine 'auto' selected: using Firecrawl (FIRECRAWL_API_KEY detected)"
        )
        chain.insert(0, "firecrawl")

    last_error = None
    for name in chain:
        try:
            logger.debug(f"Trying to use {name} to extract URL")
            return await _run_engine(url, name, config)
        except ContentCoreError as e:
            logger.debug(f"{name} failed for {url}, trying the next engine: {e}")
            last_error = e
    raise last_error


VALID_URL_ENGINES = frozenset(get_args(UrlEngine))


async def extract_from_url(url: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content from a URL using configured engine with fallback chain.

    A page with no extractable content returns ``content=""``; a failure to
    extract raises.

    Raises:
        InvalidInputError: the URL is malformed.
        NetworkError: the page (or engine API) could not be reached.
        NotFoundError: the page answered 404/410 (``simple`` engine).
        ExternalServiceError: the engine or site returned an error.
        ConfigurationError: the named engine cannot be used (e.g.
            ``crawl4ai`` not installed), or ``url_engine`` is not a known
            engine. Literal validation on the config field makes the latter
            unreachable through the model; it catches callers that assign the
            field directly.
    """
    if config.url_engine not in VALID_URL_ENGINES:
        raise ConfigurationError(
            f"Unknown URL engine: {config.url_engine!r}. "
            f"Valid values: {', '.join(get_args(UrlEngine))}"
        )

    result = await _extract_url_with_engine(url, config.url_engine, config)
    return ExtractionOutput(
        content=result.get("content", ""),
        title=result.get("title", ""),
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
    "VALID_URL_ENGINES",
    "_extract_url_with_engine",
    "extract_from_url",
    "to_typed_url_error",
    "extract_reddit",
    "is_reddit_post",
    "extract_youtube",
    "get_best_transcript",
    "get_video_title",
    "extract_transcript_pytubefix",
]
