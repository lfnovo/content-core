"""
Docling-based document extraction processor.
"""

from __future__ import annotations

import asyncio
from importlib.util import find_spec
import json
from pathlib import Path

import aiohttp

from content_core.common.exceptions import DocumentExtractionError
from content_core.config import ContentCoreConfig
from content_core.common.state import ExtractionOutput

DOCLING_AVAILABLE = find_spec("docling") is not None


def _load_docling_classes():
    """Import local Docling lazily so module import stays cheap."""
    if not DOCLING_AVAILABLE:
        raise ImportError(
            "Docling not installed. Install with: pip install content-core[docling] "
            "or use CCORE_DOCUMENT_ENGINE=simple to skip docling."
        )

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    return InputFormat, PdfPipelineOptions, DocumentConverter, PdfFormatOption


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


def _normalize_docling_api_url(api_url: str) -> str:
    """Normalize Docling Serve base URL to a stable /v1 root."""
    normalized = api_url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    if normalized.endswith("/v1/convert"):
        return normalized[: -len("/convert")]
    if normalized.endswith("/convert/file"):
        return normalized[: -len("/convert/file")]
    if normalized.endswith("/convert/source"):
        return normalized[: -len("/convert/source")]
    return f"{normalized}/v1"


def _docling_file_endpoint(api_url: str) -> str:
    return f"{_normalize_docling_api_url(api_url)}/convert/file"


def _docling_headers(config: ContentCoreConfig) -> dict[str, str]:
    headers = {"accept": "application/json"}
    if config.docling_api_key:
        headers["X-Api-Key"] = config.docling_api_key
    return headers


def _docling_form_fields(config: ContentCoreConfig) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = [
        ("to_formats", "md"),
        ("do_ocr", "true" if config.docling_ocr else "false"),
        ("abort_on_error", "true"),
    ]
    if config.docling_formulas:
        fields.append(("do_formula_enrichment", "true"))
    if config.docling_vision:
        fields.append(("do_picture_description", "true"))
        fields.append(("do_chart_extraction", "true"))
    return fields


def _extract_remote_markdown(payload: dict) -> str:
    document = payload.get("document")
    if not isinstance(document, dict):
        raise DocumentExtractionError(
            "Docling Serve returned an unexpected response: missing 'document' object."
        )

    failure = payload.get("failure") or document.get("failure")
    if failure:
        raise DocumentExtractionError(f"Docling Serve conversion failed: {failure}")

    errors = payload.get("errors") or document.get("errors")
    if errors:
        raise DocumentExtractionError(f"Docling Serve conversion failed: {errors}")

    markdown = document.get("md_content")
    if isinstance(markdown, str) and markdown.strip():
        return markdown

    status = document.get("status")
    if status and str(status).lower() not in {"success", "succeeded", "ok"}:
        raise DocumentExtractionError(
            f"Docling Serve conversion failed with status: {status}"
        )

    raise DocumentExtractionError(
        "Docling Serve returned success but no markdown content in 'document.md_content'."
    )


async def _extract_docling_remote(
    source: str, config: ContentCoreConfig
) -> ExtractionOutput:
    if not config.docling_api_url:
        raise DocumentExtractionError("Docling Serve API URL is not configured.")
    if config.docling_output_format != "markdown":
        raise DocumentExtractionError(
            "External Docling Serve extraction currently supports only docling_output_format='markdown'."
        )

    file_path = Path(source)
    endpoint = _docling_file_endpoint(config.docling_api_url)
    timeout = aiohttp.ClientTimeout(total=config.docling_timeout)
    form = aiohttp.FormData()
    for key, value in _docling_form_fields(config):
        form.add_field(key, value)
    form.add_field(
        "files",
        file_path.read_bytes(),
        filename=file_path.name,
        content_type="application/octet-stream",
    )

    try:
        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.post(
                endpoint,
                data=form,
                headers=_docling_headers(config),
                timeout=timeout,
            ) as response:
                body_text = await response.text()
                if response.status < 200 or response.status >= 300:
                    detail = body_text.strip()
                    try:
                        error_payload = json.loads(body_text) if body_text else {}
                    except json.JSONDecodeError:
                        error_payload = None
                    if isinstance(error_payload, dict):
                        detail = str(error_payload.get("detail") or detail)
                    raise DocumentExtractionError(
                        f"Docling Serve request failed with HTTP {response.status}: {detail or 'no error details returned'}"
                    )
    except aiohttp.ClientConnectorError as exc:
        raise DocumentExtractionError(
            f"Failed to connect to Docling Serve at {endpoint}: {exc}"
        ) from exc
    except OSError as exc:
        raise DocumentExtractionError(
            f"Failed to reach Docling Serve at {endpoint}: {exc}"
        ) from exc
    except aiohttp.ClientError as exc:
        raise DocumentExtractionError(f"Docling Serve request failed: {exc}") from exc
    except asyncio.TimeoutError as exc:
        raise DocumentExtractionError(
            (
                "Docling Serve request timed out "
                f"after {config.docling_timeout} seconds. "
                "Check network connectivity or increase docling_timeout."
            )
        ) from exc

    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise DocumentExtractionError(
            "Docling Serve returned invalid JSON for file conversion."
        ) from exc

    return ExtractionOutput(
        content=_extract_remote_markdown(payload),
        source_type="file",
        identified_type="",
        metadata={
            "docling_format": "markdown",
            "docling_backend": "remote",
            "docling_api_url": _normalize_docling_api_url(config.docling_api_url),
        },
    )


async def _extract_docling_local(
    source: str, config: ContentCoreConfig
) -> ExtractionOutput:
    if DOCLING_AVAILABLE:
        (
            InputFormat,
            PdfPipelineOptions,
            DocumentConverter,
            PdfFormatOption,
        ) = _load_docling_classes()
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
        _load_docling_classes()

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
        metadata={"docling_format": fmt, "docling_backend": "local"},
    )


async def extract_docling(source: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content using Docling."""
    if not source:
        raise ValueError("No input provided for Docling extraction.")

    if config.docling_api_url:
        return await _extract_docling_remote(source, config)

    return await _extract_docling_local(source, config)
