"""Environment variable parsing for engine configuration.

This module provides functions to parse engine chains from environment
variables following the naming convention:
- CCORE_ENGINE_<MIME_TYPE> for MIME types (e.g., CCORE_ENGINE_APPLICATION_PDF)
- CCORE_ENGINE_<CATEGORY> for categories (e.g., CCORE_ENGINE_DOCUMENTS)
- CCORE_FALLBACK_* for fallback configuration
"""

import os
from typing import Any, Dict, List, Optional

# Mapping from MIME types to ENV variable key suffixes
MIME_TO_ENV_KEY: Dict[str, str] = {
    # Specific MIME types
    "application/pdf": "APPLICATION_PDF",
    "application/epub+zip": "APPLICATION_EPUB",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "APPLICATION_DOCX",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "APPLICATION_XLSX",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "APPLICATION_PPTX",
    "application/msword": "APPLICATION_DOC",
    "text/html": "TEXT_HTML",
    "text/plain": "TEXT_PLAIN",
    "text/markdown": "TEXT_MARKDOWN",
    # Wildcard MIME types
    "image/*": "IMAGE",
    "audio/*": "AUDIO",
    "video/*": "VIDEO",
    "text/*": "TEXT",
}

# Mapping from categories to ENV variable key suffixes
CATEGORY_TO_ENV_KEY: Dict[str, str] = {
    "documents": "DOCUMENTS",
    "urls": "URLS",
    "audio": "AUDIO",
    "video": "VIDEO",
    "text": "TEXT",
}


def _parse_engine_list(value: str) -> List[str]:
    """Parse a comma-separated list of engine names.

    Args:
        value: Comma-separated engine names (e.g., "docling,pymupdf").

    Returns:
        List of engine names, stripped of whitespace.
    """
    if not value or not value.strip():
        return []
    return [e.strip() for e in value.split(",") if e.strip()]


def _get_env_key_for_mime_type(mime_type: str) -> Optional[str]:
    """Get the ENV key suffix for a MIME type.

    Handles both exact matches and wildcard patterns.

    Args:
        mime_type: The MIME type (e.g., "application/pdf", "image/png").

    Returns:
        The ENV key suffix, or None if no mapping exists.
    """
    # Check exact match first
    if mime_type in MIME_TO_ENV_KEY:
        return MIME_TO_ENV_KEY[mime_type]

    # Check for wildcard match (e.g., "image/*" for "image/png")
    if "/" in mime_type:
        main_type = mime_type.split("/")[0]
        wildcard_key = f"{main_type}/*"
        if wildcard_key in MIME_TO_ENV_KEY:
            return MIME_TO_ENV_KEY[wildcard_key]

    return None


def get_engine_chain_from_env_for_mime_type(mime_type: str) -> Optional[List[str]]:
    """Get engine chain from CCORE_ENGINE_{TYPE} env var for a MIME type.

    Args:
        mime_type: The MIME type to look up (e.g., "application/pdf").

    Returns:
        List of engine names, or None if not set.

    Example:
        # With CCORE_ENGINE_APPLICATION_PDF=docling-vlm,docling,pymupdf
        >>> get_engine_chain_from_env_for_mime_type("application/pdf")
        ['docling-vlm', 'docling', 'pymupdf']
    """
    env_key = _get_env_key_for_mime_type(mime_type)
    if env_key is None:
        return None

    value = os.environ.get(f"CCORE_ENGINE_{env_key}")
    if value is None:
        return None

    return _parse_engine_list(value)


def get_engine_chain_from_env_for_wildcard(mime_type: str) -> Optional[List[str]]:
    """Get engine chain for wildcard MIME type from env vars.

    Unlike get_engine_chain_from_env_for_mime_type, this only checks
    wildcard patterns (e.g., "image/*" but not "image/png").

    Args:
        mime_type: The MIME type (e.g., "image/png").

    Returns:
        List of engine names from the wildcard env var, or None.
    """
    if "/" not in mime_type:
        return None

    main_type = mime_type.split("/")[0]
    wildcard_key = MIME_TO_ENV_KEY.get(f"{main_type}/*")
    if wildcard_key is None:
        return None

    value = os.environ.get(f"CCORE_ENGINE_{wildcard_key}")
    if value is None:
        return None

    return _parse_engine_list(value)


def get_engine_chain_from_env_for_category(category: str) -> Optional[List[str]]:
    """Get engine chain from CCORE_ENGINE_{CATEGORY} env var.

    Args:
        category: The category name (e.g., "documents", "urls").

    Returns:
        List of engine names, or None if not set.

    Example:
        # With CCORE_ENGINE_DOCUMENTS=docling
        >>> get_engine_chain_from_env_for_category("documents")
        ['docling']
    """
    env_key = CATEGORY_TO_ENV_KEY.get(category)
    if env_key is None:
        return None

    value = os.environ.get(f"CCORE_ENGINE_{env_key}")
    if value is None:
        return None

    return _parse_engine_list(value)


def get_fallback_config_from_env() -> Dict[str, Any]:
    """Get fallback configuration overrides from env vars.

    Environment variables:
    - CCORE_FALLBACK_ENABLED: "true" or "false"
    - CCORE_FALLBACK_MAX_ATTEMPTS: integer
    - CCORE_FALLBACK_ON_ERROR: "next", "warn", or "fail"

    Returns:
        Dict with any configured overrides (empty if none set).
    """
    overrides: Dict[str, Any] = {}

    # CCORE_FALLBACK_ENABLED
    enabled = os.environ.get("CCORE_FALLBACK_ENABLED")
    if enabled is not None:
        overrides["enabled"] = enabled.lower() in ("true", "1", "yes", "on")

    # CCORE_FALLBACK_MAX_ATTEMPTS
    max_attempts = os.environ.get("CCORE_FALLBACK_MAX_ATTEMPTS")
    if max_attempts is not None:
        try:
            val = int(max_attempts)
            if 1 <= val <= 10:
                overrides["max_attempts"] = val
        except ValueError:
            pass  # Invalid value, ignore

    # CCORE_FALLBACK_ON_ERROR
    on_error = os.environ.get("CCORE_FALLBACK_ON_ERROR")
    if on_error is not None and on_error in ("next", "warn", "fail"):
        overrides["on_error"] = on_error

    return overrides
