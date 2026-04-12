"""
Docling-based document extraction processor.
"""

from content_core.config import ContentCoreConfig
from content_core.common.state import ExtractionOutput

DOCLING_AVAILABLE = False
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    DOCLING_AVAILABLE = True
except ImportError:
    InputFormat = None  # type: ignore
    PdfPipelineOptions = None  # type: ignore
    PdfFormatOption = None  # type: ignore

    class DocumentConverter:  # type: ignore[no-redef]
        """Stub when docling is not installed."""

        def __init__(self, **kwargs):
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
    if DOCLING_AVAILABLE and PdfPipelineOptions is not None:
        pipeline_options = PdfPipelineOptions(
            do_ocr=config.docling_ocr,
            do_formula_enrichment=config.docling_formulas,
            do_picture_description=config.docling_vision,
            do_chart_extraction=config.docling_vision,
        )
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
            }
        )
    else:
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
