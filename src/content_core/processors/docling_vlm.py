"""
VLM-based document extraction using Docling's VlmPipeline or docling-serve.

This module provides two inference modes:
- Local: Run granite-docling model directly using transformers or MLX
- Remote: Call a docling-serve API endpoint

The VLM pipeline provides enhanced document understanding through vision-language models,
offering better results for complex layouts, tables, and images compared to traditional OCR.
"""

import asyncio
import base64
import os
import platform
from typing import Any, Dict

from content_core.common.state import ProcessSourceState
from content_core.config import (
    CONFIG,
    get_docling_options,
    get_vlm_backend,
    get_vlm_inference_mode,
    get_vlm_model,
    get_vlm_remote_api_key,
    get_vlm_remote_timeout,
    get_vlm_remote_url,
)
from content_core.logging import logger

# Availability flags
DOCLING_VLM_LOCAL_AVAILABLE = False
DOCLING_VLM_MLX_AVAILABLE = False

# Try to import local VLM dependencies
try:
    from docling.datamodel.pipeline_options import VlmPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.pipeline.vlm_pipeline import VlmPipeline

    DOCLING_VLM_LOCAL_AVAILABLE = True

    # Check for MLX availability (Apple Silicon only)
    try:
        import mlx  # noqa: F401

        DOCLING_VLM_MLX_AVAILABLE = True
    except ImportError:
        pass
except ImportError:
    pass

# Try to import httpx for remote inference
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# Model specs mapping - lazily evaluated to avoid import errors
def _get_model_spec(model_name: str, backend: str):
    """Get the model specification for the given model and backend."""
    try:
        from docling.datamodel import vlm_model_specs

        # Map model names and backends to docling's naming convention
        # Docling uses MODELNAME_BACKEND format (e.g., GRANITEDOCLING_TRANSFORMERS)
        specs = {
            "granite-docling": {
                "transformers": vlm_model_specs.GRANITEDOCLING_TRANSFORMERS,
                "mlx": vlm_model_specs.GRANITEDOCLING_MLX,
            },
            "smol-docling": {
                "transformers": vlm_model_specs.SMOLDOCLING_TRANSFORMERS,
                "mlx": vlm_model_specs.SMOLDOCLING_MLX,
            },
        }
        return specs.get(model_name, {}).get(backend)
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not get model spec for {model_name}/{backend}: {e}")
        return None


def _detect_best_backend() -> str:
    """
    Auto-detect the best backend for local VLM inference.

    Returns:
        'mlx' on Apple Silicon with MLX available, otherwise 'transformers'
    """
    # Check if we're on Apple Silicon
    is_apple_silicon = (
        platform.system() == "Darwin" and platform.machine() == "arm64"
    )

    if is_apple_silicon and DOCLING_VLM_MLX_AVAILABLE:
        logger.debug("Auto-detected MLX backend (Apple Silicon)")
        return "mlx"

    logger.debug("Auto-detected transformers backend")
    return "transformers"


def _detect_best_device() -> str:
    """
    Auto-detect the best device for transformers inference.

    Returns:
        'mps' on Apple Silicon, 'cuda' if available, otherwise 'cpu'
    """
    is_apple_silicon = (
        platform.system() == "Darwin" and platform.machine() == "arm64"
    )

    if is_apple_silicon:
        return "mps"

    # Check for CUDA
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass

    return "cpu"


async def extract_with_vlm_local(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Extract document content using local VLM inference.

    Uses Docling's VlmPipeline with either transformers or MLX backend.

    Note: VlmPipelineOptions supports a subset of options compared to PdfPipelineOptions.
    Options like do_ocr, ocr_engine, table_mode, and enrichment settings are NOT applicable
    to VLM pipelines since VLM uses vision-based processing rather than traditional OCR.

    Applicable options for VLM local:
    - generate_page_images
    - generate_picture_images
    - images_scale
    - do_picture_classification
    - do_picture_description
    - document_timeout

    Args:
        state: ProcessSourceState with file_path, url, or content

    Returns:
        Dict with content and metadata updates

    Raises:
        ImportError: If docling[vlm] is not installed
        ValueError: If no valid input is provided
    """
    if not DOCLING_VLM_LOCAL_AVAILABLE:
        raise ImportError(
            "Local VLM extraction requires docling[vlm]. "
            "Install with: pip install content-core[docling-vlm]"
        )

    # Determine source
    source = state.file_path or state.url
    if not source:
        raise ValueError("VLM local extraction requires file_path or URL")

    # Get backend configuration
    backend = state.vlm_backend or get_vlm_backend()
    if backend == "auto":
        backend = _detect_best_backend()

    # Check MLX availability if requested
    if backend == "mlx" and not DOCLING_VLM_MLX_AVAILABLE:
        logger.warning("MLX backend requested but not available, falling back to transformers")
        backend = "transformers"

    # Get model configuration
    model_name = get_vlm_model()
    model_spec = _get_model_spec(model_name, backend)

    if model_spec is None:
        raise ValueError(
            f"Could not find model spec for {model_name}/{backend}. "
            f"Make sure docling[vlm] is properly installed."
        )

    logger.info(f"Using VLM local extraction with {model_name} ({backend} backend)")

    # Get docling options
    options = get_docling_options()

    # Configure pipeline options
    # Note: Use vlm_options= (not vlm_model=) to preserve inference_framework setting
    pipeline_options = VlmPipelineOptions(vlm_options=model_spec)

    # Set device for transformers backend
    if backend == "transformers":
        device = _detect_best_device()
        pipeline_options.accelerator_options.device = device
        logger.debug(f"Using device: {device}")

    # Apply options that VlmPipelineOptions supports
    # Note: VLM uses vision, so OCR/table/enrichment options don't apply
    pipeline_options.generate_page_images = options.get("generate_page_images", False)
    pipeline_options.generate_picture_images = options.get("generate_picture_images", False)
    pipeline_options.images_scale = options.get("images_scale", 1.0)
    pipeline_options.do_picture_classification = options.get("do_picture_classification", False)
    pipeline_options.do_picture_description = options.get("do_picture_description", False)

    # Apply timeout if configured
    timeout = options.get("document_timeout")
    if timeout is not None:
        pipeline_options.document_timeout = float(timeout)

    logger.debug(
        f"VLM local options: generate_page_images={options.get('generate_page_images')}, "
        f"generate_picture_images={options.get('generate_picture_images')}, "
        f"do_picture_description={options.get('do_picture_description')}"
    )

    # Create converter with VLM pipeline
    converter = DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(pipeline_cls=VlmPipeline, pipeline_options=pipeline_options)
        }
    )

    # Run conversion in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, converter.convert, source)

    doc = result.document

    # Determine output format
    cfg_fmt = (
        CONFIG.get("extraction", {}).get("docling", {}).get("output_format", "markdown")
    )
    fmt = state.output_format or state.metadata.get("docling_format") or cfg_fmt

    # Export content
    if fmt == "html":
        output = doc.export_to_html()
    elif fmt == "json":
        output = doc.export_to_json()
    else:
        output = doc.export_to_markdown()

    return {
        "content": output,
        "metadata": {
            **state.metadata,
            "docling_format": fmt,
            "vlm_backend": backend,
            "vlm_model": model_name,
            "vlm_inference": "local",
        },
    }


async def extract_with_vlm_remote(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Extract document content using remote docling-serve API.

    Args:
        state: ProcessSourceState with file_path, url, or content

    Returns:
        Dict with content and metadata updates

    Raises:
        ImportError: If httpx is not installed
        ValueError: If no valid input is provided
        RuntimeError: If the API request fails
    """
    if not HTTPX_AVAILABLE:
        raise ImportError(
            "Remote VLM extraction requires httpx. "
            "Install with: pip install content-core[docling-vlm]"
        )

    # Get remote configuration
    base_url = state.vlm_remote_url or get_vlm_remote_url()
    api_key = get_vlm_remote_api_key()
    timeout = get_vlm_remote_timeout()
    options = get_docling_options()

    # Determine output format
    cfg_fmt = (
        CONFIG.get("extraction", {}).get("docling", {}).get("output_format", "markdown")
    )
    fmt = state.output_format or state.metadata.get("docling_format") or cfg_fmt

    # Map output format to docling-serve format
    to_format_map = {
        "markdown": "md",
        "md": "md",
        "html": "html",
        "json": "json",
        "text": "text",
    }
    to_format = to_format_map.get(fmt, "md")

    # Build payload according to docling-serve API
    # See: /v1/convert/source endpoint
    # Note: VLM pipeline may run asynchronously on some servers.
    # Use "standard" pipeline for synchronous processing, or configure
    # CCORE_DOCLING_SERVE_PIPELINE env var for custom pipeline selection.
    pipeline = os.environ.get("CCORE_DOCLING_SERVE_PIPELINE", "standard")
    payload: Dict[str, Any] = {
        "options": {
            "pipeline": pipeline,
            "to_formats": [to_format],
            # OCR settings
            "do_ocr": options.get("do_ocr", True),
            "ocr_engine": options.get("ocr_engine", "easyocr"),
            "force_full_page_ocr": options.get("force_full_page_ocr", False),
            # Table settings
            "table_mode": options.get("table_mode", "accurate"),
            "do_table_structure": options.get("do_table_structure", True),
            # Enrichment settings
            "do_code_enrichment": options.get("do_code_enrichment", False),
            "do_formula_enrichment": options.get("do_formula_enrichment", True),
            # Image/picture settings
            "generate_page_images": options.get("generate_page_images", False),
            "generate_picture_images": options.get("generate_picture_images", False),
            "images_scale": options.get("images_scale", 1.0),
            "do_picture_classification": options.get("do_picture_classification", False),
            "do_picture_description": options.get("do_picture_description", False),
        },
        "sources": [],
    }

    # Add document timeout if configured
    doc_timeout = options.get("document_timeout")
    if doc_timeout is not None:
        payload["options"]["document_timeout"] = float(doc_timeout)
    logger.debug(f"Using docling-serve pipeline: {pipeline}")

    if state.url:
        # Use HTTP source
        payload["sources"].append({
            "kind": "http",
            "url": state.url,
        })
        logger.info(f"Using VLM remote extraction for URL: {state.url}")
    elif state.file_path:
        # Encode file as base64 and use file source
        if not os.path.exists(state.file_path):
            raise FileNotFoundError(f"File not found: {state.file_path}")

        with open(state.file_path, "rb") as f:
            file_content = f.read()

        payload["sources"].append({
            "kind": "file",
            "base64_string": base64.b64encode(file_content).decode("utf-8"),
            "filename": os.path.basename(state.file_path),
        })
        logger.info(f"Using VLM remote extraction for file: {state.file_path}")
    else:
        raise ValueError("VLM remote extraction requires file_path or URL")

    # Build headers
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    # Make API request to /v1/convert/source endpoint
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{base_url.rstrip('/')}/v1/convert/source",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"docling-serve API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(
                f"Failed to connect to docling-serve at {base_url}: {e}"
            ) from e

    # Parse response
    result = response.json()

    # Handle docling-serve response format
    # Response contains "document" with format-specific content
    output = ""
    if isinstance(result, dict):
        if "document" in result:
            doc_data = result["document"]
            # Try to get content in requested format
            if to_format == "md" and "md_content" in doc_data:
                output = doc_data["md_content"]
            elif to_format == "html" and "html_content" in doc_data:
                output = doc_data["html_content"]
            elif to_format == "json" and "json_content" in doc_data:
                output = doc_data["json_content"]
            elif to_format == "text" and "text_content" in doc_data:
                output = doc_data["text_content"]
            # Fallback to common field names
            elif "content" in doc_data:
                output = doc_data["content"]
            elif "markdown" in doc_data:
                output = doc_data["markdown"]
            elif "md" in doc_data:
                output = doc_data["md"]
            else:
                # Last resort: stringify the document
                import json as json_module
                output = json_module.dumps(doc_data, indent=2)
        elif "content" in result:
            output = result["content"]
        elif "result" in result:
            output = result["result"]
        else:
            # Fallback: return as JSON string
            import json as json_module
            output = json_module.dumps(result, indent=2)
    else:
        output = str(result)

    return {
        "content": output,
        "metadata": {
            **state.metadata,
            "docling_format": fmt,
            "vlm_remote_url": base_url,
            "vlm_inference": "remote",
        },
    }


async def extract_with_docling_vlm(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Extract document content using Docling VLM pipeline.

    Routes to local or remote inference based on configuration.

    Args:
        state: ProcessSourceState with file_path, url, or content

    Returns:
        Dict with content and metadata updates
    """
    # Get inference mode from state or config
    inference_mode = state.vlm_inference_mode or get_vlm_inference_mode()

    logger.debug(f"VLM inference mode: {inference_mode}")

    if inference_mode == "remote":
        return await extract_with_vlm_remote(state)
    else:
        return await extract_with_vlm_local(state)
