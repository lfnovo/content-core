"""
Docling-based document extraction processor.
"""

from content_core.common.state import ProcessSourceState
from content_core.config import CONFIG, get_docling_options
from content_core.logging import logger

DOCLING_AVAILABLE = False
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions,
        PdfPipelineOptions,
        TableFormerMode,
        TableStructureOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    DOCLING_AVAILABLE = True
except ImportError:

    class DocumentConverter:
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

# Try to import optional OCR engines
try:
    from docling.datamodel.pipeline_options import TesseractOcrOptions

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from docling.datamodel.pipeline_options import RapidOcrOptions

    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False

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


def _build_pdf_pipeline_options(options: dict) -> "PdfPipelineOptions":
    """
    Build PdfPipelineOptions from config options dict.

    Args:
        options: Dict with docling processing options from get_docling_options()

    Returns:
        Configured PdfPipelineOptions instance
    """
    pipeline_options = PdfPipelineOptions()

    # OCR settings
    pipeline_options.do_ocr = options.get("do_ocr", True)
    ocr_engine = options.get("ocr_engine", "easyocr")
    force_full_page = options.get("force_full_page_ocr", False)

    # Configure OCR engine
    if ocr_engine == "easyocr":
        pipeline_options.ocr_options = EasyOcrOptions(
            force_full_page_ocr=force_full_page
        )
    elif ocr_engine == "tesseract" and TESSERACT_AVAILABLE:
        pipeline_options.ocr_options = TesseractOcrOptions(
            force_full_page_ocr=force_full_page
        )
    elif ocr_engine == "rapidocr" and RAPIDOCR_AVAILABLE:
        pipeline_options.ocr_options = RapidOcrOptions(
            force_full_page_ocr=force_full_page
        )
    else:
        # Fallback to easyocr if requested engine not available
        if ocr_engine not in ("easyocr",):
            logger.warning(
                f"OCR engine '{ocr_engine}' not available, falling back to easyocr"
            )
        pipeline_options.ocr_options = EasyOcrOptions(
            force_full_page_ocr=force_full_page
        )

    # Table settings
    pipeline_options.do_table_structure = options.get("do_table_structure", True)
    table_mode = options.get("table_mode", "accurate")
    pipeline_options.table_structure_options = TableStructureOptions(
        mode=TableFormerMode.ACCURATE if table_mode == "accurate" else TableFormerMode.FAST
    )

    # Enrichment settings
    pipeline_options.do_code_enrichment = options.get("do_code_enrichment", False)
    pipeline_options.do_formula_enrichment = options.get("do_formula_enrichment", True)

    # Picture settings
    pipeline_options.do_picture_classification = options.get(
        "do_picture_classification", False
    )
    pipeline_options.do_picture_description = options.get(
        "do_picture_description", False
    )

    # Image generation settings
    pipeline_options.generate_page_images = options.get("generate_page_images", False)
    pipeline_options.generate_picture_images = options.get(
        "generate_picture_images", False
    )
    pipeline_options.images_scale = options.get("images_scale", 1.0)

    # Timeout setting
    timeout = options.get("document_timeout")
    if timeout is not None:
        pipeline_options.document_timeout = float(timeout)

    return pipeline_options


async def extract_with_docling(state: ProcessSourceState) -> ProcessSourceState:
    """
    Use Docling to parse files, URLs, or content into the desired format.
    """
    # Get docling options from config
    options = get_docling_options()

    # Build PDF pipeline options
    pipeline_options = _build_pdf_pipeline_options(options)

    logger.debug(
        f"Docling options: ocr={options.get('do_ocr')}, "
        f"ocr_engine={options.get('ocr_engine')}, "
        f"table_mode={options.get('table_mode')}, "
        f"formula_enrichment={options.get('do_formula_enrichment')}"
    )

    # Initialize Docling converter with configured options
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

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
