"""
Docling-based document extraction processor.
"""

import os
import warnings
from typing import Optional

from content_core.config import ContentCoreConfig
from content_core.common.messages import DOCLING_MISSING_MESSAGE
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
            raise ImportError(DOCLING_MISSING_MESSAGE)

        def convert(self, source: str):
            raise ImportError(DOCLING_MISSING_MESSAGE)

try:
    from docling.datamodel.pipeline_options import PictureDescriptionApiOptions
except ImportError:  # older docling without API-based picture description
    PictureDescriptionApiOptions = None  # type: ignore[assignment,misc]

# Env configuration for routing picture description to an OpenAI-compatible
# endpoint (vLLM, LM Studio, Ollama, MLX servers, ...). When the URL is unset,
# behavior is unchanged: docling's inline default picture description model.
VISION_URL_ENV = "CCORE_DOCLING_VISION_URL"
VISION_API_KEY_ENV = "CCORE_DOCLING_VISION_API_KEY"
VISION_MODEL_ENV = "CCORE_DOCLING_VISION_MODEL"
VISION_PROMPT_ENV = "CCORE_DOCLING_VISION_PROMPT"
VISION_MAX_TOKENS_ENV = "CCORE_DOCLING_VISION_MAX_TOKENS"
VISION_TIMEOUT_ENV = "CCORE_DOCLING_VISION_TIMEOUT"
VISION_TOKEN_PARAM_ENV = "CCORE_DOCLING_VISION_TOKEN_PARAM"

# Docling's own defaults for the picture description stage, mirrored here so
# that enabling the API path without further overrides behaves identically
# except for the endpoint.
_DEFAULT_VISION_PROMPT = "Describe the image in three sentences. Be concise and accurate."
_DEFAULT_VISION_MAX_TOKENS = 400
_DOCLING_DEFAULT_TIMEOUT = 20

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


def _parse_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        warnings.warn(
            f"{name}={raw!r} is not an integer, falling back to {default}",
            stacklevel=2,
        )
        return default


def _parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        warnings.warn(
            f"{name}={raw!r} is not a number, falling back to {default}",
            stacklevel=2,
        )
        return default


def _picture_description_options_from_env() -> Optional["PictureDescriptionApiOptions"]:
    """Build API picture description options from the CCORE_DOCLING_VISION_* env
    vars, or return None to keep docling's inline default.

    Environment is read at call time (not import time) so the endpoint can be
    reconfigured without a reload, and docling stays fully local unless
    explicitly pointed at a remote service.
    """
    url = os.getenv(VISION_URL_ENV)
    if not url or PictureDescriptionApiOptions is None:
        return None

    # The token limit field name differs across OpenAI-compatible servers:
    # newer vLLM expects max_completion_tokens, older/other servers only
    # accept max_tokens. `CCORE_DOCLING_VISION_TOKEN_PARAM` selects the name.
    token_param = os.getenv(VISION_TOKEN_PARAM_ENV, "max_completion_tokens")
    params = {token_param: _parse_int_env(VISION_MAX_TOKENS_ENV, _DEFAULT_VISION_MAX_TOKENS)}
    model = os.getenv(VISION_MODEL_ENV)
    if model:
        params["model"] = model

    # Only send an Authorization header when a key is configured; keyless
    # local servers may reject an empty bearer token.
    headers = {}
    api_key = os.getenv(VISION_API_KEY_ENV)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return PictureDescriptionApiOptions(
        url=url,
        headers=headers,
        params=params,
        prompt=os.getenv(VISION_PROMPT_ENV, _DEFAULT_VISION_PROMPT),
        timeout=_parse_float_env(VISION_TIMEOUT_ENV, _DOCLING_DEFAULT_TIMEOUT),
    )


async def extract_docling(source: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content using Docling."""
    if DOCLING_AVAILABLE and PdfPipelineOptions is not None:
        pipeline_kwargs = {}
        api_vision_options = None
        if config.docling_vision:
            api_vision_options = _picture_description_options_from_env()
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
