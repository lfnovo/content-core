"""Document extraction using Marker for high-quality markdown output.

Marker uses deep learning models to convert documents to markdown with accurate
structure preservation, table detection, and formula extraction.

Supported formats: PDF, DOCX, XLSX, PPTX, EPUB, HTML, and images.

Note: GPL-3.0 license (code) + AI Pubs Open Rail-M (models, free for <$2M revenue).
Install with: pip install content-core[marker]

Configuration (env vars or YAML):
- CCORE_MARKER_USE_LLM: Enable LLM for enhanced extraction (default: false)
- CCORE_MARKER_FORCE_OCR: Force OCR on all pages (default: false)
- CCORE_MARKER_PAGE_RANGE: Page range to extract e.g. "0-10" (default: null)
- CCORE_MARKER_OUTPUT_FORMAT: Output format (default: "markdown")
"""

import asyncio
from typing import Any, Dict, List, Optional

from content_core.common.state import ProcessSourceState
from content_core.processors.base import Processor, ProcessorResult, Source
from content_core.processors.registry import processor
from content_core.config import get_marker_options
from content_core.logging import logger

MARKER_AVAILABLE = False
SUPPORTED_MARKER_TYPES: List[str] = []

try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    MARKER_AVAILABLE = True
    # All MIME types supported by Marker
    SUPPORTED_MARKER_TYPES = [
        # PDF
        "application/pdf",
        # Office documents
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
        # EPUB
        "application/epub+zip",
        # HTML
        "text/html",
        # Images
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/tiff",
        "image/bmp",
    ]
except ImportError:
    PdfConverter = None  # type: ignore
    create_model_dict = None  # type: ignore

# Cache for the model dict (expensive to create)
_model_dict_cache: Dict[str, Any] = {}


def _get_or_create_model_dict() -> Any:
    """Get or create the model dict for Marker (cached for reuse)."""
    global _model_dict_cache

    if not _model_dict_cache:
        logger.info("Loading Marker models (first run will be slow)...")
        _model_dict_cache["artifact_dict"] = create_model_dict()
        logger.info("Marker models loaded successfully")

    return _model_dict_cache["artifact_dict"]


def _extract_with_marker_sync(file_path: str, options: dict) -> str:
    """Synchronous extraction with Marker.

    PdfConverter automatically detects file type using provider_from_filepath
    and uses the appropriate provider (PDF, DOCX, XLSX, PPTX, EPUB, HTML, Image).
    """
    if not MARKER_AVAILABLE:
        raise ImportError(
            "Marker not installed. Install with: pip install content-core[marker]"
        )

    # Get or create model dict
    artifact_dict = _get_or_create_model_dict()

    # Create converter with options
    # PdfConverter handles all file types via provider auto-detection
    converter_kwargs = {"artifact_dict": artifact_dict}

    # Apply configuration options
    if options.get("force_ocr"):
        converter_kwargs["force_ocr"] = True

    converter = PdfConverter(**converter_kwargs)

    # Convert the document (provider is auto-detected from filepath)
    result = converter(file_path)

    # Get markdown output
    return result.markdown


async def extract_with_marker(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Extract document content using Marker.

    Marker uses deep learning models to convert documents to high-quality markdown
    with accurate structure preservation, table detection, and formula extraction.

    Supports: PDF, DOCX, XLSX, PPTX, EPUB, HTML, and images.

    Args:
        state: ProcessSourceState containing the file path to extract

    Returns:
        Dict with content and metadata updates
    """
    if not MARKER_AVAILABLE:
        raise ImportError(
            "Marker not installed. Install with: pip install content-core[marker]"
        )

    file_path = state.file_path
    if not file_path:
        raise ValueError("No file path provided for Marker extraction")

    # Get options from config
    options = get_marker_options()

    logger.debug(
        f"Marker options: force_ocr={options.get('force_ocr')}, "
        f"use_llm={options.get('use_llm')}, "
        f"output_format={options.get('output_format')}"
    )

    # Run extraction in executor to avoid blocking
    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(
        None, _extract_with_marker_sync, file_path, options
    )

    return {
        "content": content,
        "metadata": {
            "extraction_engine": "marker",
            "marker_options": {
                "force_ocr": options.get("force_ocr", False),
                "use_llm": options.get("use_llm", False),
            },
        },
    }


# =============================================================================
# New Processor API (v2.0)
# =============================================================================


@processor(
    name="marker",
    mime_types=[
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/epub+zip",
        "text/html",
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/tiff",
        "image/bmp",
    ],
    extensions=[".pdf", ".docx", ".xlsx", ".pptx", ".epub", ".html", ".png", ".jpg", ".jpeg", ".gif", ".tiff", ".bmp"],
    priority=65,
    requires=["marker"],
    category="documents",
)
class MarkerProcessor(Processor):
    """Marker-based document extraction processor.

    Uses the Marker library for high-quality markdown conversion
    with deep learning models for structure preservation.
    """

    @classmethod
    def is_available(cls) -> bool:
        """Check if Marker is available."""
        return MARKER_AVAILABLE

    async def extract(
        self, source: Source, options: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Extract content using Marker.

        Args:
            source: The Source to extract content from.
            options: Optional extraction options (force_ocr, use_llm, etc.)

        Returns:
            ProcessorResult with extracted content.
        """
        if not MARKER_AVAILABLE:
            raise ImportError(
                "Marker not installed. Install with: pip install content-core[marker]"
            )

        # Convert Source to ProcessSourceState for backward compatibility
        state = ProcessSourceState(
            file_path=source.file_path,
            url=source.url,
            metadata=source.options.get("metadata", {}),
        )

        # Apply any additional options
        if options:
            if "metadata" in options:
                state.metadata.update(options["metadata"])

        # Call existing extraction function
        result = await extract_with_marker(state)

        return ProcessorResult(
            content=result.get("content", ""),
            mime_type=source.mime_type or "application/octet-stream",
            metadata=result.get("metadata", {}),
        )
