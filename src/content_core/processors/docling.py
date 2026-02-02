"""
Docling-based document extraction processor.

Picture Description:
    When do_picture_description=True, uses a VLM to generate textual descriptions
    of images found in documents. Two models are available:
    - smolvlm: SmolVLM-256M-Instruct (faster, smaller, 256M params)
    - granite: Granite Vision 3.3-2B (better quality, 2B params)

    Note: Forces CPU device due to MPS (Apple Silicon) compatibility issues.
    Descriptions are stored in pic.meta.description.text but not exported to markdown.

    Configuration:
    - CCORE_DOCLING_DO_PICTURE_DESCRIPTION=true
    - CCORE_DOCLING_PICTURE_MODEL=granite (or smolvlm)
    - CCORE_DOCLING_PICTURE_PROMPT="Your custom prompt here"
"""

from content_core.common.state import ProcessSourceState
from content_core.config import CONFIG, get_docling_options
from content_core.logging import logger

DOCLING_AVAILABLE = False
PICTURE_DESCRIPTION_AVAILABLE = False

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

    # Check if picture description models are available
    try:
        from docling.datamodel.pipeline_options import (
            PictureDescriptionVlmOptions,
            smolvlm_picture_description,
            granite_picture_description,
        )
        from docling.datamodel.accelerator_options import AcceleratorOptions

        PICTURE_DESCRIPTION_AVAILABLE = True
    except ImportError:
        pass
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
    do_picture_description = options.get("do_picture_description", False)
    pipeline_options.do_picture_description = do_picture_description

    # Configure picture description model if enabled
    if do_picture_description and PICTURE_DESCRIPTION_AVAILABLE:
        picture_model = options.get("picture_description_model", "granite").lower()
        picture_prompt = options.get(
            "picture_description_prompt",
            "Describe this image in detail. Include the type of visualization, "
            "axes labels, data trends, and any text visible in the image."
        )

        # Create custom options with the configured prompt
        if picture_model == "smolvlm":
            base_options = smolvlm_picture_description
            logger.info("Using SmolVLM-256M-Instruct for picture description")
        else:
            base_options = granite_picture_description
            logger.info("Using Granite Vision 3.3-2B for picture description")

        # Create custom options with user prompt
        pipeline_options.picture_description_options = PictureDescriptionVlmOptions(
            repo_id=base_options.repo_id,
            prompt=picture_prompt,
            generation_config={"max_new_tokens": 300, "do_sample": False},
        )

        # Force CPU device due to MPS compatibility issues with SmolVLM/Granite Vision
        pipeline_options.accelerator_options = AcceleratorOptions(device="cpu")
        logger.debug(
            f"Picture description: model={picture_model}, prompt={picture_prompt[:50]}..."
        )
    elif do_picture_description and not PICTURE_DESCRIPTION_AVAILABLE:
        logger.warning(
            "Picture description requested but VLM options not available. "
            "Install docling[vlm] for picture description support."
        )

    # Image generation settings
    pipeline_options.generate_page_images = options.get("generate_page_images", False)
    pipeline_options.generate_picture_images = options.get(
        "generate_picture_images", False
    )
    # Enable picture images when picture description is on
    if do_picture_description:
        pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = options.get("images_scale", 2.0)

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
