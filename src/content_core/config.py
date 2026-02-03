"""Configuration management for content-core.

This module provides ENV-only configuration. All configuration is done via
environment variables or programmatic setters. No YAML files are used.

Resolution order for each setting:
1. Programmatic override (set via set_*() functions)
2. Environment variable
3. Default value from defaults.py

Example:
    # Set via environment variable
    export CCORE_DOCUMENT_ENGINE=docling

    # Or programmatically
    from content_core.config import set_document_engine
    set_document_engine("docling")

    # Get the value
    from content_core.config import get_document_engine
    engine = get_document_engine()  # Returns "docling"
"""

import os
import warnings
from typing import Any, Dict, Optional, cast

from dotenv import load_dotenv

from content_core.defaults import (
    ALLOWED_DOCUMENT_ENGINES,
    ALLOWED_RETRY_OPERATIONS,
    ALLOWED_URL_ENGINES,
    ALLOWED_VLM_BACKENDS,
    ALLOWED_VLM_INFERENCE_MODES,
    ALLOWED_VLM_MODELS,
    DEFAULT_AUDIO,
    DEFAULT_CLEANUP_MODEL,
    DEFAULT_DOCLING_OPTIONS,
    DEFAULT_EXTRACTION,
    DEFAULT_FALLBACK,
    DEFAULT_FIRECRAWL,
    DEFAULT_LLM_MODEL,
    DEFAULT_MARKER_OPTIONS,
    DEFAULT_PYMUPDF_OPTIONS,
    DEFAULT_RETRY_CONFIG,
    DEFAULT_SPEECH_TO_TEXT,
    DEFAULT_SUMMARY_MODEL,
    DEFAULT_VLM_CONFIG,
    DEFAULT_YOUTUBE,
    MAX_TIMEOUT_SECONDS,
    MIN_TIMEOUT_SECONDS,
)

# Re-export for backward compatibility
__all__ = [
    "ALLOWED_DOCUMENT_ENGINES",
    "ALLOWED_URL_ENGINES",
    "ALLOWED_VLM_INFERENCE_MODES",
    "ALLOWED_VLM_BACKENDS",
    "ALLOWED_VLM_MODELS",
    "ALLOWED_RETRY_OPERATIONS",
    "MIN_TIMEOUT_SECONDS",
    "MAX_TIMEOUT_SECONDS",
    "DEFAULT_FIRECRAWL_API_URL",
    "DEFAULT_RETRY_CONFIG",
    # Functions
    "get_document_engine",
    "get_url_engine",
    "get_audio_concurrency",
    "get_firecrawl_api_url",
    "get_retry_config",
    "get_docling_options",
    "get_vlm_inference_mode",
    "get_vlm_backend",
    "get_vlm_model",
    "get_vlm_remote_url",
    "get_vlm_remote_api_key",
    "get_vlm_remote_timeout",
    "get_marker_options",
    "get_pymupdf_options",
    "get_youtube_preferred_languages",
    "get_extraction_config",
    "get_fallback_config",
    "get_model_config",
    # Setters
    "set_document_engine",
    "set_url_engine",
    "set_audio_concurrency",
    "set_firecrawl_api_url",
    "set_docling_output_format",
    "set_vlm_inference_mode",
    "set_vlm_backend",
    "set_vlm_model",
    "set_vlm_remote_url",
    "set_vlm_remote_api_key",
    "set_vlm_remote_timeout",
    "set_pymupdf_ocr_enabled",
    "set_pymupdf_formula_threshold",
    "set_pymupdf_ocr_fallback",
    # Config management
    "reset_config",
    "reset_extraction_config",
]

# Load environment variables from .env file
load_dotenv()

# Warn about deprecated CCORE_CONFIG_PATH
if os.environ.get("CCORE_CONFIG_PATH") or os.environ.get("CCORE_MODEL_CONFIG_PATH"):
    warnings.warn(
        "CCORE_CONFIG_PATH and CCORE_MODEL_CONFIG_PATH are deprecated and ignored. "
        "Configuration is now done via environment variables only. "
        "See docs/configuration.md for the new ENV-based configuration.",
        DeprecationWarning,
        stacklevel=1,
    )

# Backward compatibility alias
DEFAULT_FIRECRAWL_API_URL = DEFAULT_FIRECRAWL["api_url"]

# =============================================================================
# Programmatic Overrides Storage
# =============================================================================

# Stores programmatic overrides set via set_*() functions
# Format: {"setting_name": value}
_OVERRIDES: Dict[str, Any] = {}

# Cached extraction config instance
_extraction_config = None


def reset_config():
    """Reset all programmatic overrides.

    This clears all values set via set_*() functions. Useful for testing.
    After calling this, get_*() functions will return ENV values or defaults.
    """
    global _extraction_config
    _OVERRIDES.clear()
    _extraction_config = None


def reset_extraction_config():
    """Reset only the cached extraction config (backward compatibility).

    Prefer using reset_config() which resets everything.
    """
    global _extraction_config
    _extraction_config = None


# =============================================================================
# Helper Functions
# =============================================================================


def _parse_bool(value: str) -> bool:
    """Parse a boolean from string."""
    return value.lower() in ("true", "1", "yes", "on")


def _parse_optional_int(value: str) -> Optional[int]:
    """Parse an optional integer (None for 'null', 'none', '')."""
    if value.lower() in ("null", "none", ""):
        return None
    return int(value)


def _parse_optional_float(value: str) -> Optional[float]:
    """Parse an optional float (None for 'null', 'none', '')."""
    if value.lower() in ("null", "none", ""):
        return None
    return float(value)


def _parse_optional_str(value: str) -> Optional[str]:
    """Parse an optional string (None for 'null', 'none', '')."""
    if value.lower() in ("null", "none", ""):
        return None
    return value


def _warn_invalid(var_name: str, value: str, reason: str, default: Any):
    """Log a warning for invalid configuration values."""
    from content_core.logging import logger

    logger.warning(
        f"Invalid {var_name}: '{value}'. {reason}. Using default: {default}"
    )


# =============================================================================
# Engine Selection
# =============================================================================


def get_document_engine() -> str:
    """Get document engine.

    Resolution order:
    1. Programmatic override via set_document_engine()
    2. CCORE_DOCUMENT_ENGINE environment variable
    3. Default: "auto"

    Returns:
        str: Engine name ('auto', 'simple', 'docling', 'docling-vlm', 'marker')
    """
    # 1. Programmatic override
    if "document_engine" in _OVERRIDES:
        return _OVERRIDES["document_engine"]

    # 2. Environment variable
    env_engine = os.environ.get("CCORE_DOCUMENT_ENGINE")
    if env_engine:
        if env_engine not in ALLOWED_DOCUMENT_ENGINES:
            _warn_invalid(
                "CCORE_DOCUMENT_ENGINE",
                env_engine,
                f"Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_ENGINES))}",
                DEFAULT_EXTRACTION["document_engine"],
            )
            return DEFAULT_EXTRACTION["document_engine"]
        return env_engine

    # 3. Default
    return DEFAULT_EXTRACTION["document_engine"]


def set_document_engine(engine: str):
    """Override the document extraction engine.

    Args:
        engine: Engine name ('auto', 'simple', 'docling', 'docling-vlm', 'marker')
    """
    _OVERRIDES["document_engine"] = engine


def get_url_engine() -> str:
    """Get URL engine.

    Resolution order:
    1. Programmatic override via set_url_engine()
    2. CCORE_URL_ENGINE environment variable
    3. Default: "auto"

    Returns:
        str: Engine name ('auto', 'simple', 'firecrawl', 'jina', 'crawl4ai')
    """
    # 1. Programmatic override
    if "url_engine" in _OVERRIDES:
        return _OVERRIDES["url_engine"]

    # 2. Environment variable
    env_engine = os.environ.get("CCORE_URL_ENGINE")
    if env_engine:
        if env_engine not in ALLOWED_URL_ENGINES:
            _warn_invalid(
                "CCORE_URL_ENGINE",
                env_engine,
                f"Allowed: {', '.join(sorted(ALLOWED_URL_ENGINES))}",
                DEFAULT_EXTRACTION["url_engine"],
            )
            return DEFAULT_EXTRACTION["url_engine"]
        return env_engine

    # 3. Default
    return DEFAULT_EXTRACTION["url_engine"]


def set_url_engine(engine: str):
    """Override the URL extraction engine.

    Args:
        engine: Engine name ('auto', 'simple', 'firecrawl', 'jina', 'crawl4ai')
    """
    _OVERRIDES["url_engine"] = engine


# =============================================================================
# Audio Configuration
# =============================================================================


def get_audio_concurrency() -> int:
    """Get audio concurrency (number of parallel transcriptions).

    Resolution order:
    1. Programmatic override via set_audio_concurrency()
    2. CCORE_AUDIO_CONCURRENCY environment variable
    3. Default: 3

    Returns:
        int: Number of concurrent transcriptions (1-10)
    """
    default = DEFAULT_AUDIO["concurrency"]

    # 1. Programmatic override
    if "audio_concurrency" in _OVERRIDES:
        return _OVERRIDES["audio_concurrency"]

    # 2. Environment variable
    env_val = os.environ.get("CCORE_AUDIO_CONCURRENCY")
    if env_val:
        try:
            concurrency = int(env_val)
            if 1 <= concurrency <= 10:
                return concurrency
            _warn_invalid(
                "CCORE_AUDIO_CONCURRENCY",
                env_val,
                "Must be between 1 and 10",
                default,
            )
        except ValueError:
            _warn_invalid(
                "CCORE_AUDIO_CONCURRENCY",
                env_val,
                "Must be a valid integer",
                default,
            )

    # 3. Default
    return default


def set_audio_concurrency(concurrency: int):
    """Override the audio concurrency setting.

    Args:
        concurrency: Number of concurrent audio transcriptions (1-10)

    Raises:
        ValueError: If concurrency is not between 1 and 10
    """
    if not isinstance(concurrency, int) or concurrency < 1 or concurrency > 10:
        raise ValueError(
            f"Audio concurrency must be an integer between 1 and 10, got: {concurrency}"
        )
    _OVERRIDES["audio_concurrency"] = concurrency


# =============================================================================
# Firecrawl Configuration
# =============================================================================


def get_firecrawl_api_url() -> str:
    """Get the Firecrawl API URL.

    Resolution order:
    1. Programmatic override via set_firecrawl_api_url()
    2. FIRECRAWL_API_BASE_URL environment variable
    3. Default: "https://api.firecrawl.dev"

    Returns:
        str: The Firecrawl API URL
    """
    # 1. Programmatic override
    if "firecrawl_api_url" in _OVERRIDES:
        return _OVERRIDES["firecrawl_api_url"]

    # 2. Environment variable
    env_url = os.environ.get("FIRECRAWL_API_BASE_URL")
    if env_url:
        return env_url

    # 3. Default
    return DEFAULT_FIRECRAWL["api_url"]


def set_firecrawl_api_url(api_url: str):
    """Override the Firecrawl API URL.

    Args:
        api_url: The Firecrawl API URL (e.g., 'http://localhost:3002')
    """
    _OVERRIDES["firecrawl_api_url"] = api_url


# =============================================================================
# Retry Configuration
# =============================================================================


def get_retry_config(operation_type: str) -> dict:
    """Get retry configuration for a specific operation type.

    Resolution order:
    1. Environment variables (CCORE_{TYPE}_MAX_RETRIES, etc.)
    2. Default values

    Args:
        operation_type: One of 'youtube', 'url_api', 'url_network', 'audio', 'llm', 'download'

    Returns:
        dict: Configuration with 'max_attempts', 'base_delay', 'max_delay'
    """
    if operation_type not in ALLOWED_RETRY_OPERATIONS:
        from content_core.logging import logger

        logger.warning(
            f"Unknown retry operation type: '{operation_type}'. "
            f"Allowed values: {', '.join(sorted(ALLOWED_RETRY_OPERATIONS))}. "
            f"Using default config for 'url_network'."
        )
        operation_type = "url_network"

    # Get defaults
    defaults = DEFAULT_RETRY_CONFIG.get(
        operation_type, DEFAULT_RETRY_CONFIG["url_network"]
    )

    max_attempts = defaults["max_attempts"]
    base_delay: float = defaults["base_delay"]
    max_delay: float = defaults["max_delay"]

    # Environment variable overrides
    env_prefix = f"CCORE_{operation_type.upper()}"

    # Max retries
    env_max_retries = os.environ.get(f"{env_prefix}_MAX_RETRIES")
    if env_max_retries:
        try:
            val = int(env_max_retries)
            if 1 <= val <= 20:
                max_attempts = val
            else:
                _warn_invalid(
                    f"{env_prefix}_MAX_RETRIES",
                    env_max_retries,
                    "Must be between 1 and 20",
                    max_attempts,
                )
        except ValueError:
            _warn_invalid(
                f"{env_prefix}_MAX_RETRIES",
                env_max_retries,
                "Must be a valid integer",
                max_attempts,
            )

    # Base delay
    env_base_delay = os.environ.get(f"{env_prefix}_BASE_DELAY")
    if env_base_delay:
        try:
            val = float(env_base_delay)
            if 0.1 <= val <= 60:
                base_delay = val
            else:
                _warn_invalid(
                    f"{env_prefix}_BASE_DELAY",
                    env_base_delay,
                    "Must be between 0.1 and 60",
                    base_delay,
                )
        except ValueError:
            _warn_invalid(
                f"{env_prefix}_BASE_DELAY",
                env_base_delay,
                "Must be a valid number",
                base_delay,
            )

    # Max delay
    env_max_delay = os.environ.get(f"{env_prefix}_MAX_DELAY")
    if env_max_delay:
        try:
            val = float(env_max_delay)
            if 1 <= val <= 300:
                max_delay = val
            else:
                _warn_invalid(
                    f"{env_prefix}_MAX_DELAY",
                    env_max_delay,
                    "Must be between 1 and 300",
                    max_delay,
                )
        except ValueError:
            _warn_invalid(
                f"{env_prefix}_MAX_DELAY",
                env_max_delay,
                "Must be a valid number",
                max_delay,
            )

    return {
        "max_attempts": max_attempts,
        "base_delay": base_delay,
        "max_delay": max_delay,
    }


# =============================================================================
# Docling Configuration
# =============================================================================


def get_docling_options() -> dict:
    """Get docling processing options.

    Resolution order for each option:
    1. Environment variable (CCORE_DOCLING_*)
    2. Default value

    Environment variable overrides:
    - CCORE_DOCLING_DO_OCR: Enable OCR (true/false)
    - CCORE_DOCLING_OCR_ENGINE: OCR engine (easyocr, tesseract, etc.)
    - CCORE_DOCLING_FORCE_FULL_PAGE_OCR: Force OCR on entire page (true/false)
    - CCORE_DOCLING_TABLE_MODE: Table extraction mode (accurate, fast)
    - CCORE_DOCLING_DO_TABLE_STRUCTURE: Extract table structure (true/false)
    - CCORE_DOCLING_DO_CODE_ENRICHMENT: Enable code enrichment (true/false)
    - CCORE_DOCLING_DO_FORMULA_ENRICHMENT: Enable formula enrichment (true/false)
    - CCORE_DOCLING_GENERATE_PAGE_IMAGES: Generate page images (true/false)
    - CCORE_DOCLING_GENERATE_PICTURE_IMAGES: Generate picture images (true/false)
    - CCORE_DOCLING_IMAGES_SCALE: Image scale factor (float)
    - CCORE_DOCLING_DO_PICTURE_CLASSIFICATION: Enable picture classification (true/false)
    - CCORE_DOCLING_DO_PICTURE_DESCRIPTION: Enable picture description (true/false)
    - CCORE_DOCLING_PICTURE_MODEL: Picture description model (granite, smolvlm)
    - CCORE_DOCLING_PICTURE_PROMPT: Custom prompt for picture description
    - CCORE_DOCLING_OUTPUT_FORMAT: Output format (markdown, html, json)
    - CCORE_DOCLING_DOCUMENT_TIMEOUT: Document processing timeout in seconds

    Returns:
        dict: Options for docling processing
    """
    # Start with defaults
    options = DEFAULT_DOCLING_OPTIONS.copy()

    # Apply programmatic overrides first
    if "docling_output_format" in _OVERRIDES:
        options["output_format"] = _OVERRIDES["docling_output_format"]

    # Environment variable mappings
    env_mappings = {
        "CCORE_DOCLING_DO_OCR": ("do_ocr", _parse_bool),
        "CCORE_DOCLING_OCR_ENGINE": ("ocr_engine", str),
        "CCORE_DOCLING_FORCE_FULL_PAGE_OCR": ("force_full_page_ocr", _parse_bool),
        "CCORE_DOCLING_TABLE_MODE": ("table_mode", str),
        "CCORE_DOCLING_DO_TABLE_STRUCTURE": ("do_table_structure", _parse_bool),
        "CCORE_DOCLING_DO_CODE_ENRICHMENT": ("do_code_enrichment", _parse_bool),
        "CCORE_DOCLING_DO_FORMULA_ENRICHMENT": ("do_formula_enrichment", _parse_bool),
        "CCORE_DOCLING_GENERATE_PAGE_IMAGES": ("generate_page_images", _parse_bool),
        "CCORE_DOCLING_GENERATE_PICTURE_IMAGES": ("generate_picture_images", _parse_bool),
        "CCORE_DOCLING_IMAGES_SCALE": ("images_scale", _parse_optional_float),
        "CCORE_DOCLING_DO_PICTURE_CLASSIFICATION": ("do_picture_classification", _parse_bool),
        "CCORE_DOCLING_DO_PICTURE_DESCRIPTION": ("do_picture_description", _parse_bool),
        "CCORE_DOCLING_PICTURE_MODEL": ("picture_description_model", str),
        "CCORE_DOCLING_PICTURE_PROMPT": ("picture_description_prompt", str),
        "CCORE_DOCLING_OUTPUT_FORMAT": ("output_format", str),
        "CCORE_DOCLING_DOCUMENT_TIMEOUT": ("document_timeout", _parse_optional_int),
    }

    for env_var, (option_key, converter) in env_mappings.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            try:
                options[option_key] = converter(env_val)
            except (ValueError, TypeError):
                from content_core.logging import logger

                logger.warning(f"Invalid {env_var}: '{env_val}'. Using default.")

    return options


def set_docling_output_format(fmt: str):
    """Override Docling output_format.

    Args:
        fmt: Output format ('markdown', 'html', or 'json')
    """
    _OVERRIDES["docling_output_format"] = fmt


# Backward compatibility aliases
def get_vlm_options() -> dict:
    """Alias for get_docling_options() for backward compatibility."""
    return get_docling_options()


def get_vlm_remote_options() -> dict:
    """Alias for get_docling_options() for backward compatibility."""
    return get_docling_options()


# =============================================================================
# VLM Configuration
# =============================================================================


def get_vlm_inference_mode() -> str:
    """Get VLM inference mode.

    Resolution order:
    1. Programmatic override via set_vlm_inference_mode()
    2. CCORE_VLM_INFERENCE_MODE environment variable
    3. Default: 'local'

    Returns:
        str: 'local' or 'remote'
    """
    default = DEFAULT_VLM_CONFIG["inference_mode"]

    # 1. Programmatic override
    if "vlm_inference_mode" in _OVERRIDES:
        return _OVERRIDES["vlm_inference_mode"]

    # 2. Environment variable
    env_mode = os.environ.get("CCORE_VLM_INFERENCE_MODE")
    if env_mode:
        if env_mode not in ALLOWED_VLM_INFERENCE_MODES:
            _warn_invalid(
                "CCORE_VLM_INFERENCE_MODE",
                env_mode,
                f"Allowed: {', '.join(sorted(ALLOWED_VLM_INFERENCE_MODES))}",
                default,
            )
            return default
        return env_mode

    # 3. Default
    return default


def set_vlm_inference_mode(mode: str):
    """Override the VLM inference mode.

    Args:
        mode: 'local' for local inference, 'remote' for docling-serve

    Raises:
        ValueError: If mode is not 'local' or 'remote'
    """
    if mode not in ALLOWED_VLM_INFERENCE_MODES:
        raise ValueError(
            f"VLM inference mode must be one of {ALLOWED_VLM_INFERENCE_MODES}, got: {mode}"
        )
    _OVERRIDES["vlm_inference_mode"] = mode


def get_vlm_backend() -> str:
    """Get VLM backend.

    Resolution order:
    1. Programmatic override via set_vlm_backend()
    2. CCORE_VLM_BACKEND environment variable
    3. Default: 'auto'

    Returns:
        str: 'auto', 'transformers', or 'mlx'
    """
    default = DEFAULT_VLM_CONFIG["backend"]

    # 1. Programmatic override
    if "vlm_backend" in _OVERRIDES:
        return _OVERRIDES["vlm_backend"]

    # 2. Environment variable
    env_backend = os.environ.get("CCORE_VLM_BACKEND")
    if env_backend:
        if env_backend not in ALLOWED_VLM_BACKENDS:
            _warn_invalid(
                "CCORE_VLM_BACKEND",
                env_backend,
                f"Allowed: {', '.join(sorted(ALLOWED_VLM_BACKENDS))}",
                default,
            )
            return default
        return env_backend

    # 3. Default
    return default


def set_vlm_backend(backend: str):
    """Override the VLM backend.

    Args:
        backend: 'auto', 'transformers', or 'mlx'

    Raises:
        ValueError: If backend is not valid
    """
    if backend not in ALLOWED_VLM_BACKENDS:
        raise ValueError(
            f"VLM backend must be one of {ALLOWED_VLM_BACKENDS}, got: {backend}"
        )
    _OVERRIDES["vlm_backend"] = backend


def get_vlm_model() -> str:
    """Get VLM model.

    Resolution order:
    1. Programmatic override via set_vlm_model()
    2. CCORE_VLM_MODEL environment variable
    3. Default: 'granite-docling'

    Returns:
        str: 'granite-docling' or 'smol-docling'
    """
    default = DEFAULT_VLM_CONFIG["model"]

    # 1. Programmatic override
    if "vlm_model" in _OVERRIDES:
        return _OVERRIDES["vlm_model"]

    # 2. Environment variable
    env_model = os.environ.get("CCORE_VLM_MODEL")
    if env_model:
        if env_model not in ALLOWED_VLM_MODELS:
            _warn_invalid(
                "CCORE_VLM_MODEL",
                env_model,
                f"Allowed: {', '.join(sorted(ALLOWED_VLM_MODELS))}",
                default,
            )
            return default
        return env_model

    # 3. Default
    return default


def set_vlm_model(model: str):
    """Override the VLM model.

    Args:
        model: 'granite-docling' or 'smol-docling'

    Raises:
        ValueError: If model is not valid
    """
    if model not in ALLOWED_VLM_MODELS:
        raise ValueError(
            f"VLM model must be one of {ALLOWED_VLM_MODELS}, got: {model}"
        )
    _OVERRIDES["vlm_model"] = model


def get_vlm_remote_url() -> str:
    """Get docling-serve URL.

    Resolution order:
    1. Programmatic override via set_vlm_remote_url()
    2. CCORE_DOCLING_SERVE_URL environment variable
    3. Default: 'http://localhost:5001'

    Returns:
        str: The docling-serve URL
    """
    # 1. Programmatic override
    if "vlm_remote_url" in _OVERRIDES:
        return _OVERRIDES["vlm_remote_url"]

    # 2. Environment variable
    env_url = os.environ.get("CCORE_DOCLING_SERVE_URL")
    if env_url:
        return env_url

    # 3. Default
    return DEFAULT_VLM_CONFIG["remote_url"]


def set_vlm_remote_url(url: str):
    """Override the docling-serve URL.

    Args:
        url: The URL of the docling-serve endpoint
    """
    _OVERRIDES["vlm_remote_url"] = url


def get_vlm_remote_api_key() -> Optional[str]:
    """Get docling-serve API key.

    Resolution order:
    1. Programmatic override via set_vlm_remote_api_key()
    2. CCORE_DOCLING_SERVE_API_KEY environment variable
    3. Default: None

    Returns:
        str | None: The API key or None if not configured
    """
    # 1. Programmatic override
    if "vlm_remote_api_key" in _OVERRIDES:
        return _OVERRIDES["vlm_remote_api_key"]

    # 2. Environment variable
    env_key = os.environ.get("CCORE_DOCLING_SERVE_API_KEY")
    if env_key:
        return env_key

    # 3. Default
    return DEFAULT_VLM_CONFIG["remote_api_key"]


def set_vlm_remote_api_key(api_key: Optional[str]):
    """Override the docling-serve API key.

    Args:
        api_key: The API key for authentication, or None to disable
    """
    _OVERRIDES["vlm_remote_api_key"] = api_key


def get_vlm_remote_timeout() -> int:
    """Get docling-serve timeout.

    Resolution order:
    1. Programmatic override via set_vlm_remote_timeout()
    2. CCORE_DOCLING_SERVE_TIMEOUT environment variable
    3. Default: 120 seconds

    Returns:
        int: Timeout in seconds
    """
    default = DEFAULT_VLM_CONFIG["remote_timeout"]

    # 1. Programmatic override
    if "vlm_remote_timeout" in _OVERRIDES:
        return _OVERRIDES["vlm_remote_timeout"]

    # 2. Environment variable
    env_timeout = os.environ.get("CCORE_DOCLING_SERVE_TIMEOUT")
    if env_timeout:
        try:
            timeout = int(env_timeout)
            if MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS:
                return timeout
            _warn_invalid(
                "CCORE_DOCLING_SERVE_TIMEOUT",
                env_timeout,
                f"Must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS}",
                default,
            )
        except ValueError:
            _warn_invalid(
                "CCORE_DOCLING_SERVE_TIMEOUT",
                env_timeout,
                "Must be a valid integer",
                default,
            )

    # 3. Default
    return default


def set_vlm_remote_timeout(timeout: int):
    """Override the docling-serve timeout.

    Args:
        timeout: Timeout in seconds (1-3600)

    Raises:
        ValueError: If timeout is out of range
    """
    if timeout < MIN_TIMEOUT_SECONDS or timeout > MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"VLM remote timeout must be between {MIN_TIMEOUT_SECONDS} and "
            f"{MAX_TIMEOUT_SECONDS} seconds, got: {timeout}"
        )
    _OVERRIDES["vlm_remote_timeout"] = timeout


# =============================================================================
# PyMuPDF Configuration
# =============================================================================


def get_pymupdf_options() -> dict:
    """Get PyMuPDF processing options.

    Resolution order for each option:
    1. Programmatic override
    2. Environment variable
    3. Default value

    Environment variable overrides:
    - CCORE_PYMUPDF_ENABLE_FORMULA_OCR: Enable OCR for formula-heavy pages (true/false)
    - CCORE_PYMUPDF_FORMULA_THRESHOLD: Minimum formulas per page to trigger OCR (int)
    - CCORE_PYMUPDF_OCR_FALLBACK: Fallback to standard extraction if OCR fails (true/false)

    Returns:
        dict: Options for PyMuPDF processing
    """
    # Start with defaults
    options = DEFAULT_PYMUPDF_OPTIONS.copy()

    # Apply programmatic overrides
    if "pymupdf_enable_formula_ocr" in _OVERRIDES:
        options["enable_formula_ocr"] = _OVERRIDES["pymupdf_enable_formula_ocr"]
    if "pymupdf_formula_threshold" in _OVERRIDES:
        options["formula_threshold"] = _OVERRIDES["pymupdf_formula_threshold"]
    if "pymupdf_ocr_fallback" in _OVERRIDES:
        options["ocr_fallback"] = _OVERRIDES["pymupdf_ocr_fallback"]

    # Environment variable overrides
    env_mappings = {
        "CCORE_PYMUPDF_ENABLE_FORMULA_OCR": ("enable_formula_ocr", _parse_bool),
        "CCORE_PYMUPDF_FORMULA_THRESHOLD": ("formula_threshold", int),
        "CCORE_PYMUPDF_OCR_FALLBACK": ("ocr_fallback", _parse_bool),
    }

    for env_var, (option_key, converter) in env_mappings.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            try:
                options[option_key] = converter(env_val)
            except (ValueError, TypeError):
                from content_core.logging import logger

                logger.warning(f"Invalid {env_var}: '{env_val}'. Using default.")

    return options


def set_pymupdf_ocr_enabled(enabled: bool):
    """Enable or disable PyMuPDF OCR for formula-heavy pages."""
    _OVERRIDES["pymupdf_enable_formula_ocr"] = enabled


def set_pymupdf_formula_threshold(threshold: int):
    """Set the minimum number of formulas per page to trigger OCR."""
    _OVERRIDES["pymupdf_formula_threshold"] = threshold


def set_pymupdf_ocr_fallback(enabled: bool):
    """Enable or disable fallback to standard extraction when OCR fails."""
    _OVERRIDES["pymupdf_ocr_fallback"] = enabled


# =============================================================================
# Marker Configuration
# =============================================================================


def get_marker_options() -> dict:
    """Get Marker processing options.

    Resolution order for each option:
    1. Environment variable
    2. Default value

    Environment variable overrides:
    - CCORE_MARKER_USE_LLM: Enable LLM for enhanced extraction (true/false)
    - CCORE_MARKER_FORCE_OCR: Force OCR on all pages (true/false)
    - CCORE_MARKER_PAGE_RANGE: Page range to extract e.g. "0-10" (null for all)
    - CCORE_MARKER_OUTPUT_FORMAT: Output format (markdown, json, html)

    Returns:
        dict: Options for Marker processing
    """
    # Start with defaults
    options = DEFAULT_MARKER_OPTIONS.copy()

    # Environment variable overrides
    env_mappings = {
        "CCORE_MARKER_USE_LLM": ("use_llm", _parse_bool),
        "CCORE_MARKER_FORCE_OCR": ("force_ocr", _parse_bool),
        "CCORE_MARKER_PAGE_RANGE": ("page_range", _parse_optional_str),
        "CCORE_MARKER_OUTPUT_FORMAT": ("output_format", str),
    }

    for env_var, (option_key, converter) in env_mappings.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            try:
                options[option_key] = converter(env_val)
            except (ValueError, TypeError):
                from content_core.logging import logger

                logger.warning(f"Invalid {env_var}: '{env_val}'. Using default.")

    return options


# =============================================================================
# YouTube Configuration
# =============================================================================


def get_youtube_preferred_languages() -> list:
    """Get YouTube preferred languages for transcript extraction.

    Resolution order:
    1. CCORE_YOUTUBE_LANGUAGES environment variable (comma-separated)
    2. Default: ["en", "es", "pt"]

    Returns:
        list: List of language codes
    """
    # Environment variable
    env_langs = os.environ.get("CCORE_YOUTUBE_LANGUAGES")
    if env_langs:
        return [lang.strip() for lang in env_langs.split(",") if lang.strip()]

    # Default
    return DEFAULT_YOUTUBE["preferred_languages"].copy()


# =============================================================================
# Model Configuration
# =============================================================================


def get_model_config(model_alias: str) -> dict:
    """Get model configuration for Esperanto integration.

    Resolution order:
    1. Environment variables (CCORE_{MODEL}_PROVIDER, etc.)
    2. Default values

    Args:
        model_alias: One of 'speech_to_text', 'default_model', 'cleanup_model', 'summary_model'

    Returns:
        dict: Model configuration with provider, model_name, and config

    Raises:
        ValueError: If model_alias is unknown
    """
    # Map aliases to defaults
    defaults_map = {
        "speech_to_text": DEFAULT_SPEECH_TO_TEXT,
        "default_model": DEFAULT_LLM_MODEL,
        "cleanup_model": DEFAULT_CLEANUP_MODEL,
        "summary_model": DEFAULT_SUMMARY_MODEL,
    }

    if model_alias not in defaults_map:
        raise ValueError(
            f"Unknown model alias: {model_alias}. "
            f"Allowed: {', '.join(sorted(defaults_map.keys()))}"
        )

    # Start with defaults (deep copy for nested dicts)
    import copy
    config = copy.deepcopy(defaults_map[model_alias])

    # Environment variable overrides
    env_prefix = f"CCORE_{model_alias.upper()}"

    # Provider
    env_provider = os.environ.get(f"{env_prefix}_PROVIDER")
    if env_provider:
        config["provider"] = env_provider

    # Model name
    env_model = os.environ.get(f"{env_prefix}_MODEL")
    if env_model:
        config["model_name"] = env_model

    # Timeout (for STT) or config.timeout (for LLM)
    env_timeout = os.environ.get(f"{env_prefix}_TIMEOUT")
    if env_timeout:
        try:
            timeout = int(env_timeout)
            if model_alias == "speech_to_text":
                config["timeout"] = timeout
            else:
                config.setdefault("config", {})["timeout"] = timeout
        except ValueError:
            pass

    # Also check ESPERANTO_LLM_TIMEOUT / ESPERANTO_STT_TIMEOUT for backward compat
    if model_alias == "speech_to_text":
        esperanto_timeout = os.environ.get("ESPERANTO_STT_TIMEOUT")
        if esperanto_timeout and "timeout" not in config:
            try:
                config["timeout"] = int(esperanto_timeout)
            except ValueError:
                pass
    else:
        esperanto_timeout = os.environ.get("ESPERANTO_LLM_TIMEOUT")
        if esperanto_timeout:
            try:
                timeout = int(esperanto_timeout)
                cfg = config.setdefault("config", {})
                if "timeout" not in cfg:
                    cfg["timeout"] = timeout
            except ValueError:
                pass

    return config


# =============================================================================
# Extraction Config (for EngineResolver)
# =============================================================================


def get_extraction_config():
    """Get the extraction configuration for EngineResolver.

    This function returns an ExtractionConfig instance that includes
    fallback config and engine settings from ENV variables.

    Returns:
        ExtractionConfig: The extraction configuration.
    """
    from content_core.engine_config.env import get_fallback_config_from_env
    from content_core.engine_config.schema import ExtractionConfig, FallbackConfig

    global _extraction_config
    if _extraction_config is not None:
        return _extraction_config

    # Build fallback config from ENV
    fallback_env = get_fallback_config_from_env()
    fallback_config = FallbackConfig(
        enabled=fallback_env.get("enabled", DEFAULT_FALLBACK["enabled"]),
        max_attempts=fallback_env.get("max_attempts", DEFAULT_FALLBACK["max_attempts"]),
        on_error=fallback_env.get("on_error", DEFAULT_FALLBACK["on_error"]),
        fatal_errors=DEFAULT_FALLBACK["fatal_errors"],
    )

    # Get timeout from ENV
    timeout = DEFAULT_EXTRACTION["timeout"]
    env_timeout = os.environ.get("CCORE_EXTRACTION_TIMEOUT")
    if env_timeout:
        try:
            timeout = int(env_timeout)
        except ValueError:
            pass

    # Build extraction config
    # Note: engines dict is empty - engine resolution is done via ENV vars directly
    _extraction_config = ExtractionConfig(
        timeout=timeout,
        engines={},  # No YAML engines - all via ENV
        fallback=fallback_config,
        engine_options={},  # Options come from get_*_options() functions
        document_engine=get_document_engine(),
        url_engine=get_url_engine(),
    )

    return _extraction_config


def get_fallback_config():
    """Get the fallback configuration for extraction.

    This is a convenience wrapper around get_extraction_config().

    Returns:
        FallbackConfig: The fallback configuration.
    """
    return get_extraction_config().fallback


# =============================================================================
# Backward Compatibility - CONFIG dict
# =============================================================================

# For backward compatibility, provide a CONFIG dict that processors can use
# This is populated lazily from ENV and defaults
class _ConfigProxy:
    """Proxy object that provides backward-compatible CONFIG dict access."""

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value with backward-compatible paths."""
        if key == "youtube_transcripts":
            return {"preferred_languages": get_youtube_preferred_languages()}
        elif key == "extraction":
            return {
                "document_engine": get_document_engine(),
                "url_engine": get_url_engine(),
                "docling": {
                    "output_format": get_docling_options()["output_format"],
                    "options": get_docling_options(),
                    "vlm": {
                        "inference_mode": get_vlm_inference_mode(),
                        "local": {
                            "backend": get_vlm_backend(),
                            "model": get_vlm_model(),
                        },
                        "remote": {
                            "url": get_vlm_remote_url(),
                            "api_key": get_vlm_remote_api_key(),
                            "timeout": get_vlm_remote_timeout(),
                        },
                    },
                },
                "pymupdf": get_pymupdf_options(),
                "marker": {"options": get_marker_options()},
                "audio": {"concurrency": get_audio_concurrency()},
                "firecrawl": {"api_url": get_firecrawl_api_url()},
                "fallback": {
                    "enabled": DEFAULT_FALLBACK["enabled"],
                    "max_attempts": DEFAULT_FALLBACK["max_attempts"],
                    "on_error": DEFAULT_FALLBACK["on_error"],
                    "fatal_errors": DEFAULT_FALLBACK["fatal_errors"],
                },
            }
        elif key == "speech_to_text":
            return get_model_config("speech_to_text")
        elif key == "default_model":
            return get_model_config("default_model")
        elif key == "cleanup_model":
            return get_model_config("cleanup_model")
        elif key == "summary_model":
            return get_model_config("summary_model")
        elif key == "retry":
            return {op: get_retry_config(op) for op in ALLOWED_RETRY_OPERATIONS}
        return default

    def setdefault(self, key: str, default: Any = None) -> Any:
        """Setdefault is a no-op for the proxy - use set_*() functions."""
        return self.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access."""
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __contains__(self, key: str) -> bool:
        """Check if key exists."""
        return key in (
            "youtube_transcripts",
            "extraction",
            "speech_to_text",
            "default_model",
            "cleanup_model",
            "summary_model",
            "retry",
        )


# Backward compatibility: CONFIG dict for processors
CONFIG = _ConfigProxy()
