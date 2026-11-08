"""
Docling-based document extraction processor.
"""

from typing import Optional

from content_core.config import ContentCoreConfig
from content_core.common.messages import DOCLING_MISSING_MESSAGE
from content_core.common.state import ExtractionOutput
from content_core.logging import logger

DOCLING_AVAILABLE = False
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions,
        PictureDescriptionApiOptions,
    )
    from docling.document_converter import DocumentConverter, PdfFormatOption

    DOCLING_AVAILABLE = True
except ImportError:
    InputFormat = None  # type: ignore
    PdfPipelineOptions = None  # type: ignore
    PictureDescriptionApiOptions = None  # type: ignore
    PdfFormatOption = None  # type: ignore

    class DocumentConverter:  # type: ignore[no-redef]
        """Stub when docling is not installed."""

        def __init__(self, **kwargs):
            raise ImportError(DOCLING_MISSING_MESSAGE)

        def convert(self, source: str):
            raise ImportError(DOCLING_MISSING_MESSAGE)

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


def _picture_description_api_options(
    config: ContentCoreConfig,
) -> Optional["PictureDescriptionApiOptions"]:
    """Build the options that send picture description to an OpenAI-compatible
    endpoint, or return None to keep docling's inline default model.

    ``docling_vision_url`` is the switch: without it, nothing leaves the
    machine and the other ``docling_vision_*`` settings are ignored.
    """
    if not config.docling_vision_url or PictureDescriptionApiOptions is None:
        return None

    # The token limit field name differs across OpenAI-compatible servers:
    # newer ones expect max_completion_tokens, older ones only accept
    # max_tokens. docling_vision_token_param selects the name.
    params: dict = {config.docling_vision_token_param: config.docling_vision_max_tokens}
    if config.docling_vision_model:
        params["model"] = config.docling_vision_model

    # Only send an Authorization header when a key is configured; keyless
    # local servers may reject an empty bearer token.
    headers = {}
    if config.docling_vision_api_key:
        headers["Authorization"] = f"Bearer {config.docling_vision_api_key}"

    kwargs = {}
    if config.docling_vision_prompt:
        kwargs["prompt"] = config.docling_vision_prompt

    logger.debug(
        f"Docling picture description via {config.docling_vision_url} "
        f"(model={config.docling_vision_model or 'server default'})"
    )
    return PictureDescriptionApiOptions(
        url=config.docling_vision_url,
        headers=headers,
        params=params,
        timeout=config.docling_vision_timeout,
        **kwargs,
    )


async def extract_docling(source: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content using Docling."""
    if DOCLING_AVAILABLE and PdfPipelineOptions is not None:
        pipeline_kwargs = {}
        api_vision_options = None
        if config.docling_vision:
            api_vision_options = _picture_description_api_options(config)
            if api_vision_options is not None:
                pipeline_kwargs["picture_description_options"] = api_vision_options
        pipeline_options = PdfPipelineOptions(
            do_ocr=config.docling_ocr,
            do_formula_enrichment=config.docling_formulas,
            do_picture_description=config.docling_vision,
            do_chart_extraction=config.docling_vision,
            enable_remote_services=api_vision_options is not None,
            **pipeline_kwargs,
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
