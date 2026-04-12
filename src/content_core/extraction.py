"""Content extraction orchestrator -- replaces LangGraph state graph."""
from __future__ import annotations

import os
import tempfile
from urllib.parse import urlparse

import aiohttp

from content_core.common.exceptions import InvalidInputError, UnsupportedTypeException
from content_core.common.retry import retry_download
from content_core.config import ContentCoreConfig, get_default_config
from content_core.logging import logger
from content_core.common.state import ExtractionOutput

# Import processor v2 functions
from content_core.processors.media.audio import transcribe_audio
from content_core.processors.document import SUPPORTED_OFFICE_TYPES, extract_office
from content_core.processors.document.pdf import SUPPORTED_PDF_TYPES, extract_pdf_file
from content_core.processors.document.epub import SUPPORTED_EPUB_TYPES, extract_epub_file
from content_core.processors.text import extract_text_file, process_text
from content_core.processors.url import detect_remote_mime, extract_from_url
from content_core.processors.media.video import extract_video
from content_core.processors.url.reddit import extract_reddit, is_reddit_post
from content_core.processors.url.youtube import extract_youtube

# Optional docling
try:
    from content_core.processors.document.docling import (
        DOCLING_AVAILABLE,
        DOCLING_SUPPORTED,
        extract_docling,
    )
except ImportError:
    DOCLING_AVAILABLE = False
    DOCLING_SUPPORTED = set()
    extract_docling = None  # type: ignore


async def extract_content(
    *,
    url: str | None = None,
    file_path: str | None = None,
    content: str | None = None,
    config: ContentCoreConfig | None = None,
) -> ExtractionOutput:
    """Main extraction entry point.

    Args:
        url: URL to extract content from.
        file_path: Local file path to extract content from.
        content: Raw text or HTML content to process.
        config: Optional config override. If None, uses default config.

    Returns:
        ExtractionOutput with extracted content
    """
    cfg = config or get_default_config()

    if content:
        return await process_text(content, cfg)
    elif url:
        return await _extract_url(url, cfg)
    elif file_path:
        return await _extract_file(file_path, cfg)
    else:
        raise InvalidInputError("No source provided: set content, url, or file_path")


async def _extract_url(url: str, cfg: ContentCoreConfig) -> ExtractionOutput:
    """Route URL to appropriate processor."""
    # YouTube detection
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"):
        return await extract_youtube(url, cfg)

    # Reddit detection — use JSON endpoint, fall back to normal extraction
    if is_reddit_post(url):
        result = await extract_reddit(url, cfg)
        if result and result.content:
            return result
        logger.debug("Reddit JSON extraction failed, falling back to normal URL extraction")

    # Check MIME type via HEAD request
    mime = await detect_remote_mime(url)

    # Downloadable file types (PDFs, Office docs, etc served over HTTP)
    downloadable = set(SUPPORTED_PDF_TYPES) | set(SUPPORTED_EPUB_TYPES) | set(SUPPORTED_OFFICE_TYPES)
    if DOCLING_AVAILABLE:
        downloadable |= set(DOCLING_SUPPORTED)
    downloadable.discard("text/html")  # HTML is treated as web content, not downloaded

    if mime in downloadable:
        tmp_path = await _download_remote_file(url)
        try:
            result = await _extract_file(tmp_path, cfg, delete_after=True)
            result.source_type = "url"
            return result
        except Exception:
            _safe_delete(tmp_path)
            raise

    # Treat as article/webpage
    return await extract_from_url(url, cfg)


async def _extract_file(
    path: str, cfg: ContentCoreConfig, delete_after: bool = False
) -> ExtractionOutput:
    """Route file to appropriate processor based on detected MIME type."""
    from content_core.content.identification import get_file_type

    mime = await get_file_type(path)
    logger.debug(f"Detected file type: {mime} for {path}")

    used_docling = False
    try:
        # Docling routing (if enabled and supported)
        engine = cfg.document_engine
        if engine == "docling" or (
            engine == "auto" and DOCLING_AVAILABLE and mime in DOCLING_SUPPORTED
        ):
            if DOCLING_AVAILABLE and extract_docling is not None:
                used_docling = True
                result = await extract_docling(path, cfg)
                if not result.title:
                    result.title = os.path.basename(path)
                result.identified_type = mime
                result.source_type = "file"
                return result

        # Standard processors
        if mime in SUPPORTED_PDF_TYPES:
            result = await extract_pdf_file(path, cfg)
        elif mime in SUPPORTED_EPUB_TYPES:
            result = await extract_epub_file(path, cfg)
        elif mime in SUPPORTED_OFFICE_TYPES:
            result = await extract_office(path, mime, cfg)
        elif mime.startswith("video/"):
            result = await extract_video(path, cfg)
        elif mime.startswith("audio/"):
            result = await transcribe_audio(path, cfg)
        elif mime == "text/plain":
            result = await extract_text_file(path, cfg)
        else:
            raise UnsupportedTypeException(f"Unsupported file type: {mime}")

        if not used_docling and (cfg.docling_formulas or cfg.docling_vision or not cfg.docling_ocr):
            logger.warning(
                "Docling enrichment flags (docling_formulas, docling_vision, docling_ocr) "
                "are only applied when document_engine='docling'. "
                "Set CCORE_DOCUMENT_ENGINE=docling or pass --engine docling."
            )

        if not result.title:
            result.title = os.path.basename(path)
        result.identified_type = mime
        result.source_type = "file"
        return result
    finally:
        if delete_after:
            _safe_delete(path)


@retry_download()
async def _fetch_remote_file(url: str) -> tuple:
    """Download a remote file. Wrapped with retry logic."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "").split(";", 1)[0]
            content = await resp.read()
            return mime, content


async def _download_remote_file(url: str) -> str:
    """Download a remote file to a temp path."""
    logger.debug(f"Downloading remote file: {url}")
    mime, content = await _fetch_remote_file(url)
    suffix = os.path.splitext(urlparse(url).path)[1] if urlparse(url).path else ""
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(content)
    return tmp


def _safe_delete(path: str) -> None:
    """Delete a file, ignoring errors."""
    try:
        os.remove(path)
    except OSError:
        logger.warning(f"Failed to delete temp file: {path}")
