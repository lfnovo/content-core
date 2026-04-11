from content_core.common import ProcessSourceState
from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.models_v2 import ExtractionOutput

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


async def extract_office_content(state: ProcessSourceState):
    """Universal function to extract content from Office files"""
    assert state.file_path, "No file path provided"
    assert state.identified_type in SUPPORTED_OFFICE_TYPES, "Unsupported File Type"
    file_path = state.file_path
    doc_type = state.identified_type

    if (
        doc_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        logger.debug("Extracting content from DOCX file")
        content = await extract_docx_content_detailed(file_path)
        info = await get_docx_info(file_path)
    elif (
        doc_type
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ):
        logger.debug("Extracting content from PPTX file")
        content = await extract_pptx_content(file_path)
        info = await get_pptx_info(file_path)
    elif (
        doc_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        logger.debug("Extracting content from XLSX file")
        content = await extract_xlsx_content(file_path)
        info = await get_xlsx_info(file_path)
    else:
        raise Exception(f"Unsupported file format: {doc_type}")

    del info["content"]
    return {"content": content, "metadata": info}


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


__all__ = [
    "SUPPORTED_OFFICE_TYPES",
    "extract_docx_content_detailed",
    "get_docx_info",
    "extract_pptx_content",
    "get_pptx_info",
    "extract_xlsx_content",
    "get_xlsx_info",
    "extract_office_content",
    "extract_office",
]
