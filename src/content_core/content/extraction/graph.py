import os
import tempfile
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import aiohttp
from langgraph.graph import END, START, StateGraph

from content_core.common import (
    ProcessSourceInput,
    ProcessSourceState,
    UnsupportedTypeException,
)
from content_core.config import get_document_engine
from content_core.logging import logger
from content_core.processors.audio import extract_audio_data  # type: ignore
try:
    from content_core.processors.docling import (
        DOCLING_SUPPORTED,  # type: ignore
        extract_with_docling,
        DOCLING_AVAILABLE,
    )
except ImportError:
    DOCLING_AVAILABLE = False
    DOCLING_SUPPORTED = set()
    extract_with_docling = None
from content_core.processors.office import (
    SUPPORTED_OFFICE_TYPES,
    extract_office_content,
)
from content_core.processors.pdf import SUPPORTED_FITZ_TYPES, extract_pdf
from content_core.processors.text import extract_txt
from content_core.processors.url import extract_url, url_provider
from content_core.processors.video import extract_best_audio_from_video
from content_core.processors.youtube import extract_youtube_transcript


async def source_identification(state: ProcessSourceState) -> Dict[str, str]:
    """
    Identify the content source based on parameters
    """
    if state.content:
        doc_type = "text"
    elif state.file_path:
        doc_type = "file"
    elif state.url:
        doc_type = "url"
    else:
        raise ValueError("No source provided.")

    return {"source_type": doc_type}


async def file_type(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Identify the file using pure Python file detection
    """
    from content_core.content.identification import get_file_type
    
    return_dict = {}
    file_path = state.file_path
    if file_path is not None:
        return_dict["identified_type"] = await get_file_type(file_path)
        return_dict["title"] = os.path.basename(file_path)
    return return_dict


async def file_type_edge(data: ProcessSourceState) -> str:
    assert data.identified_type, "Type not identified"
    identified_type = data.identified_type
    logger.debug(f"Identified type: {identified_type}")

    if identified_type == "text/plain":
        return "extract_txt"
    elif identified_type in SUPPORTED_FITZ_TYPES:
        return "extract_pdf"
    elif identified_type in SUPPORTED_OFFICE_TYPES:
        return "extract_office_content"
    elif identified_type.startswith("video"):
        return "extract_best_audio_from_video"
    elif identified_type.startswith("audio"):
        return "extract_audio_data"
    else:
        raise UnsupportedTypeException(f"Unsupported file type: {data.identified_type}")


async def delete_file(data: ProcessSourceState) -> Dict[str, Any]:
    if data.delete_source:
        logger.debug(f"Deleting file: {data.file_path}")
        file_path = data.file_path
        if file_path is not None:
            try:
                os.remove(file_path)
                return {"file_path": None}
            except FileNotFoundError:
                logger.warning(f"File not found while trying to delete: {file_path}")
    else:
        logger.debug("Not deleting file")
    return {}


async def url_type_router(x: ProcessSourceState) -> Optional[str]:
    assert x.identified_type, "Type not identified"
    return x.identified_type


async def source_type_router(x: ProcessSourceState) -> Optional[str]:
    assert x.source_type, "Source type not identified"
    return x.source_type


async def download_remote_file(state: ProcessSourceState) -> Dict[str, Any]:
    url = state.url
    assert url, "No URL provided"
    logger.debug(f"Downloading remote file: {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "").split(";", 1)[0]
            suffix = (
                os.path.splitext(urlparse(url).path)[1] if urlparse(url).path else ""
            )
            fd, tmp = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            with open(tmp, "wb") as f:
                f.write(await resp.read())
    return {"file_path": tmp, "identified_type": mime}


async def file_type_router_docling(state: ProcessSourceState) -> str:
    """
    Route to Docling if enabled and supported; otherwise use simple file type edge.
    Supports 'auto', 'docling', and 'simple'.
    'auto' tries docling first, then falls back to simple if docling fails.
    """
    # Use environment-aware engine selection
    engine = state.document_engine or get_document_engine()
    
    if engine == "auto":
        logger.debug("Using auto engine")
        # Check if docling is available AND supports the file type
        if DOCLING_AVAILABLE and state.identified_type in DOCLING_SUPPORTED:
            logger.debug("Using docling extraction (auto mode)")
            return "extract_docling"
        # Fallback to simple
        logger.debug("Falling back to simple extraction (docling unavailable or unsupported)")
        return await file_type_edge(state)

    if engine == "docling":
        if not DOCLING_AVAILABLE:
            raise ImportError("Docling engine requested but docling package not installed. Install with: pip install content-core[docling]")
        if state.identified_type in DOCLING_SUPPORTED:
            logger.debug("Using docling engine")
            return "extract_docling"
        # If docling doesn't support this file type, fall back to simple
        logger.debug("Docling doesn't support this file type, using simple engine")
        return await file_type_edge(state)
    
    # For 'simple' or any other engine
    logger.debug("Using simple engine")
    return await file_type_edge(state)


# Create workflow
workflow = StateGraph(
    ProcessSourceState, input=ProcessSourceInput, output=ProcessSourceState
)

# Add nodes
workflow.add_node("source", source_identification)
workflow.add_node("url_provider", url_provider)
workflow.add_node("file_type", file_type)
workflow.add_node("extract_txt", extract_txt)
workflow.add_node("extract_pdf", extract_pdf)
workflow.add_node("extract_url", extract_url)
workflow.add_node("extract_office_content", extract_office_content)
workflow.add_node("extract_best_audio_from_video", extract_best_audio_from_video)
workflow.add_node("extract_audio_data", extract_audio_data)
workflow.add_node("extract_youtube_transcript", extract_youtube_transcript)
workflow.add_node("delete_file", delete_file)
workflow.add_node("download_remote_file", download_remote_file)
# Only add docling node if available
if DOCLING_AVAILABLE:
    workflow.add_node("extract_docling", extract_with_docling)

# Add edges
workflow.add_edge(START, "source")
workflow.add_conditional_edges(
    "source",
    source_type_router,
    {
        "url": "url_provider",
        "file": "file_type",
        "text": END,
    },
)
workflow.add_conditional_edges(
    "file_type",
    file_type_router_docling,
)
workflow.add_conditional_edges(
    "url_provider",
    url_type_router,
    {
        **{
            m: "download_remote_file"
            for m in list(SUPPORTED_FITZ_TYPES)
            + list(SUPPORTED_OFFICE_TYPES)
            + list(DOCLING_SUPPORTED)
            if m not in ["text/html"]  # Exclude HTML from file download, treat as web content
        },
        "article": "extract_url",
        "text/html": "extract_url",  # Route HTML content to URL extraction
        "youtube": "extract_youtube_transcript",
    },
)
workflow.add_edge("url_provider", END)
workflow.add_edge("file_type", END)
workflow.add_edge("extract_url", END)
workflow.add_edge("extract_txt", END)
workflow.add_edge("extract_youtube_transcript", END)

workflow.add_edge("extract_pdf", "delete_file")
workflow.add_edge("extract_office_content", "delete_file")
workflow.add_edge("extract_best_audio_from_video", "extract_audio_data")
workflow.add_edge("extract_audio_data", "delete_file")
workflow.add_edge("delete_file", END)
workflow.add_edge("download_remote_file", "file_type")

graph = workflow.compile()
