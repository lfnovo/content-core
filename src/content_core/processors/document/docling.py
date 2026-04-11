"""
Docling-based document extraction processor.
"""

from content_core.config import ContentCoreConfig
from content_core.common.state import ExtractionOutput

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


async def extract_docling(source: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content using Docling."""
    converter = DocumentConverter()

    if not source:
        raise ValueError("No input provided for Docling extraction.")

    result = converter.convert(source)
    doc = result.document

    fmt = config.docling_output_format
    if fmt == "html":
        output = doc.export_to_html()
    elif fmt == "json":
        output = doc.export_to_json()
    else:
        output = doc.export_to_markdown()

    return ExtractionOutput(
        content=output,
        source_type="file",
        identified_type="",
        metadata={"docling_format": fmt},
    )
