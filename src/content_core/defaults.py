"""Default configuration values for content-core.

All defaults are defined here. No YAML files are needed.
Configuration can be overridden via environment variables or programmatic setters.
"""

from typing import Dict, List, Any

# =============================================================================
# Extraction Defaults
# =============================================================================

DEFAULT_EXTRACTION: Dict[str, Any] = {
    "timeout": 300,
    "document_engine": "auto",
    "url_engine": "auto",
}

DEFAULT_AUDIO: Dict[str, Any] = {
    "concurrency": 3,
}

DEFAULT_FIRECRAWL: Dict[str, Any] = {
    "api_url": "https://api.firecrawl.dev",
}

# =============================================================================
# Fallback Defaults
# =============================================================================

DEFAULT_FALLBACK: Dict[str, Any] = {
    "enabled": True,
    "max_attempts": 3,
    "on_error": "warn",  # "next" | "warn" | "fail"
    "fatal_errors": [
        "FileNotFoundError",
        "PermissionError",
        "ValidationError",
        "FatalExtractionError",
    ],
}

# =============================================================================
# Retry Defaults
# =============================================================================

DEFAULT_RETRY_CONFIG: Dict[str, Dict[str, Any]] = {
    "youtube": {"max_attempts": 5, "base_delay": 2, "max_delay": 60},
    "url_api": {"max_attempts": 3, "base_delay": 1, "max_delay": 30},
    "url_network": {"max_attempts": 3, "base_delay": 0.5, "max_delay": 10},
    "audio": {"max_attempts": 3, "base_delay": 2, "max_delay": 30},
    "llm": {"max_attempts": 3, "base_delay": 1, "max_delay": 30},
    "download": {"max_attempts": 3, "base_delay": 1, "max_delay": 15},
}

# =============================================================================
# Docling Defaults
# =============================================================================

DEFAULT_DOCLING_OPTIONS: Dict[str, Any] = {
    # OCR settings - enabled by default for scanned PDFs
    "do_ocr": True,
    "ocr_engine": "easyocr",  # easyocr | tesseract | tesserocr | rapidocr | ocrmac
    "force_full_page_ocr": False,
    # Table settings - accurate mode by default for better quality
    "table_mode": "accurate",  # accurate | fast
    "do_table_structure": True,
    # Enrichment settings
    "do_code_enrichment": False,
    "do_formula_enrichment": True,  # Enabled for scientific papers
    # Image/picture settings - minimal by default
    "generate_page_images": False,
    "generate_picture_images": False,
    "images_scale": 2.0,  # Higher resolution for better VLM processing
    "do_picture_classification": False,
    "do_picture_description": False,
    # Picture description settings (used when do_picture_description=True)
    # Note: Forces CPU device due to MPS compatibility issues
    "picture_description_model": "granite",  # smolvlm (256M) | granite (2B, better)
    "picture_description_prompt": (
        "Describe this image in detail. Include the type of visualization, "
        "axes labels, data trends, and any text visible in the image."
    ),
    # Output format
    "output_format": "markdown",  # markdown | html | json
    # Timeout - no limit by default
    "document_timeout": None,
}

DEFAULT_VLM_CONFIG: Dict[str, Any] = {
    "inference_mode": "local",  # local | remote
    "backend": "auto",  # auto | transformers | mlx
    "model": "granite-docling",  # granite-docling | smol-docling
    "remote_url": "http://localhost:5001",
    "remote_api_key": None,
    "remote_timeout": 120,
}

# =============================================================================
# PyMuPDF Defaults
# =============================================================================

DEFAULT_PYMUPDF_OPTIONS: Dict[str, Any] = {
    "enable_formula_ocr": False,
    "formula_threshold": 3,
    "ocr_fallback": True,
}

# =============================================================================
# Marker Defaults
# =============================================================================

DEFAULT_MARKER_OPTIONS: Dict[str, Any] = {
    "use_llm": False,
    "force_ocr": False,
    "page_range": None,
    "output_format": "markdown",
}

# =============================================================================
# Model Defaults (for Esperanto integration)
# =============================================================================

DEFAULT_SPEECH_TO_TEXT: Dict[str, Any] = {
    "provider": "openai",
    "model_name": "gpt-4o-transcribe-diarize",
    "timeout": 3600,  # 1 hour for long audio files
}

DEFAULT_LLM_MODEL: Dict[str, Any] = {
    "provider": "openai",
    "model_name": "gpt-4o-mini",
    "config": {
        "temperature": 0.5,
        "top_p": 1,
        "max_tokens": 2000,
        "timeout": 300,
    },
}

DEFAULT_CLEANUP_MODEL: Dict[str, Any] = {
    "provider": "openai",
    "model_name": "gpt-4o-mini",
    "config": {
        "temperature": 0,
        "max_tokens": 8000,
        "output_format": "json",
        "timeout": 600,
    },
}

DEFAULT_SUMMARY_MODEL: Dict[str, Any] = {
    "provider": "openai",
    "model_name": "gpt-4o-mini",
    "config": {
        "temperature": 0,
        "top_p": 1,
        "max_tokens": 2000,
        "timeout": 300,
    },
}

# =============================================================================
# YouTube Defaults
# =============================================================================

DEFAULT_YOUTUBE: Dict[str, Any] = {
    "preferred_languages": ["en", "es", "pt"],
}

# =============================================================================
# Allowed Values (for validation)
# =============================================================================

ALLOWED_DOCUMENT_ENGINES = {"auto", "simple", "docling", "docling-vlm", "marker"}
ALLOWED_URL_ENGINES = {"auto", "simple", "firecrawl", "jina", "crawl4ai"}
ALLOWED_VLM_INFERENCE_MODES = {"local", "remote"}
ALLOWED_VLM_BACKENDS = {"auto", "transformers", "mlx"}
ALLOWED_VLM_MODELS = {"granite-docling", "smol-docling"}
ALLOWED_RETRY_OPERATIONS = {
    "youtube",
    "url_api",
    "url_network",
    "audio",
    "llm",
    "download",
}

# Timeout validation bounds (seconds)
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 3600
