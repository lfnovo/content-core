"""
PDF extraction using pymupdf4llm for LLM-optimized markdown output.

This processor uses pymupdf4llm to extract content from PDFs with:
- Proper markdown formatting (headers, bold, italic, code)
- Table detection and conversion to markdown
- Multi-column layout support
- Image extraction (optional)
- Better structure preservation than basic PyMuPDF

Note: This module is optional - PyMuPDF uses AGPL-3.0 license.
Install with: pip install content-core[pymupdf]

Reference: https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/
"""

import asyncio
from typing import Any, Dict, List

from content_core.common.state import ProcessSourceState
from content_core.config import CONFIG
from content_core.logging import logger

# pymupdf4llm availability check (AGPL-3.0 license - optional dependency)
PYMUPDF4LLM_AVAILABLE = False
SUPPORTED_PYMUPDF4LLM_TYPES: List[str] = []

try:
    import pymupdf4llm  # type: ignore
    PYMUPDF4LLM_AVAILABLE = True
    SUPPORTED_PYMUPDF4LLM_TYPES = [
        "application/pdf",
        "application/epub+zip",
    ]
except ImportError:
    pymupdf4llm = None  # type: ignore


async def extract_with_pymupdf4llm(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Extract document content using pymupdf4llm for LLM-optimized output.

    This provides better markdown formatting than the basic PyMuPDF extraction,
    including proper headers, tables, and structure preservation.

    Args:
        state: ProcessSourceState with file_path

    Returns:
        Dict with content and metadata updates

    Raises:
        ImportError: If pymupdf4llm is not installed
        ValueError: If no file_path is provided
        FileNotFoundError: If file doesn't exist
    """
    if not PYMUPDF4LLM_AVAILABLE:
        raise ImportError(
            "pymupdf4llm is required for this extraction method. "
            "Install with: pip install content-core[pymupdf]"
        )

    if not state.file_path:
        raise ValueError("pymupdf4llm extraction requires a file_path")

    file_path = state.file_path
    logger.info(f"Extracting with pymupdf4llm: {file_path}")

    # Get configuration options
    llm_config = CONFIG.get("extraction", {}).get("pymupdf4llm", {})

    # Build options from config with sensible defaults
    options = {
        "page_chunks": llm_config.get("page_chunks", False),
        "write_images": llm_config.get("write_images", False),
        "embed_images": llm_config.get("embed_images", False),
        "show_progress": False,  # Don't show progress bar in library mode
    }

    # Optional: specific pages
    if state.metadata.get("pages"):
        options["pages"] = state.metadata["pages"]

    # Optional: image settings
    if options["write_images"]:
        options["image_path"] = llm_config.get("image_path", "./images")
        options["image_format"] = llm_config.get("image_format", "png")
        options["dpi"] = llm_config.get("dpi", 150)

    def _extract():
        """Run extraction in thread pool."""
        return pymupdf4llm.to_markdown(file_path, **options)

    # Run CPU-bound extraction in thread pool
    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(None, _extract)

    # Handle page_chunks output (list of dicts)
    if options["page_chunks"] and isinstance(content, list):
        # Join page chunks into single markdown
        markdown_parts = []
        for i, chunk in enumerate(content):
            if isinstance(chunk, dict) and "text" in chunk:
                markdown_parts.append(chunk["text"])
            elif isinstance(chunk, str):
                markdown_parts.append(chunk)
        content = "\n\n---\n\n".join(markdown_parts)

    logger.debug(f"pymupdf4llm extracted {len(content)} characters")

    return {
        "content": content,
        "metadata": {
            **state.metadata,
            "extraction_engine": "pymupdf4llm",
        },
    }
