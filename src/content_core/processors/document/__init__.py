from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput

# Import from sub-modules
from content_core.processors.document.docx import (
    extract_docx_content_detailed,
    get_docx_info,
)
from content_core.processors.document.pptx import (
    extract_pptx_content,
    get_pptx_info,
)
from content_core.processors.document.xlsx import (
    extract_xlsx_content,
    get_xlsx_info,
)

SUPPORTED_OFFICE_TYPES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]


async def extract_office(
    file_path: str, mime_type: str, config: ContentCoreConfig
) -> ExtractionOutput:
    """Extract content from an Office document (DOCX/PPTX/XLSX).

    Unlike the legacy extract_office_content, this function does NOT call the
    get_*_info helpers, avoiding the double-extraction bug where content was
    read twice.
    """
    if mime_type not in SUPPORTED_OFFICE_TYPES:
        raise ValueError(f"Unsupported Office MIME type: {mime_type}")

    if (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        logger.debug("Extracting content from DOCX file")
        content = await extract_docx_content_detailed(file_path)
    elif (
        mime_type
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ):
        logger.debug("Extracting content from PPTX file")
        content = await extract_pptx_content(file_path)
    elif (
        mime_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        logger.debug("Extracting content from XLSX file")
        content = await extract_xlsx_content(file_path)
    else:
        raise ValueError(f"Unsupported file format: {mime_type}")

    return ExtractionOutput(
        content=content or "",
        source_type="file",
        identified_type=mime_type,
    )


from content_core.processors.document.pdf import (
    SUPPORTED_PDF_TYPES,
    clean_pdf_text,
    convert_table_to_markdown,
    count_formula_placeholders,
    extract_pdf_file,
)
from content_core.processors.document.epub import (
    SUPPORTED_EPUB_TYPES,
    extract_epub_file,
)

__all__ = [
    "SUPPORTED_OFFICE_TYPES",
    "SUPPORTED_PDF_TYPES",
    "SUPPORTED_EPUB_TYPES",
    "extract_docx_content_detailed",
    "get_docx_info",
    "extract_pptx_content",
    "get_pptx_info",
    "extract_xlsx_content",
    "get_xlsx_info",
    "extract_office",
    "clean_pdf_text",
    "convert_table_to_markdown",
    "count_formula_placeholders",
    "extract_pdf_file",
    "extract_epub_file",
]
