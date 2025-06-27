"""
Docling-based document extraction processor.
"""

from content_core.common.state import ProcessSourceState
from content_core.config import CONFIG

DOCLING_AVAILABLE = False
try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except ImportError:

    class DocumentConverter:
        """Stub when docling is not installed."""

        def __init__(self):
            raise ImportError(
                "Docling not installed. Install with: pip install content-core[docling] "
                "or use CCORE_DOCUMENT_ENGINE=simple to skip docling."
            )

        def convert(self, source: str):
            raise ImportError(
                "Docling not installed. Install with: pip install content-core[docling] "
                "or use CCORE_DOCUMENT_ENGINE=simple to skip docling."
            )

# Supported MIME types for Docling extraction
DOCLING_SUPPORTED = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/markdown",
    # "text/plain", #docling currently not supporting txt
    "text/x-markdown",
    "text/csv",
    "text/html",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
}


async def extract_with_docling(state: ProcessSourceState) -> ProcessSourceState:
    """
    Use Docling to parse files, URLs, or content into the desired format.
    """
    # Initialize Docling converter
    converter = DocumentConverter()

    # Determine source: file path, URL, or direct content
    source = state.file_path or state.url or state.content
    if not source:
        raise ValueError("No input provided for Docling extraction.")

    # Convert document
    result = converter.convert(source)
    doc = result.document

    # Determine output format (per execution override, metadata, then config)
    cfg_fmt = (
        CONFIG.get("extraction", {}).get("docling", {}).get("output_format", "markdown")
    )
    fmt = state.output_format or state.metadata.get("docling_format") or cfg_fmt
    # Record the format used
    state.metadata["docling_format"] = fmt
    if fmt == "html":
        output = doc.export_to_html()
    elif fmt == "json":
        output = doc.export_to_json()
    else:
        output = doc.export_to_markdown()

    # Update state
    state.content = output
    return state
