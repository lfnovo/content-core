"""Engine configuration module for content-core.

This module provides configuration management for content extraction,
including engine selection, fallback behavior, and environment variable
overrides.

Example usage:
    from content_core.engine_config import EngineResolver, ExtractionConfig

    config = ExtractionConfig(
        engines={
            "application/pdf": ["docling-vlm", "docling"],
            "documents": "docling",
        },
        fallback=FallbackConfig(max_attempts=3),
    )
    resolver = EngineResolver(config)
    engines = resolver.resolve("application/pdf")
"""

from content_core.engine_config.env import (
    CATEGORY_TO_ENV_KEY,
    MIME_TO_ENV_KEY,
    get_engine_chain_from_env_for_category,
    get_engine_chain_from_env_for_mime_type,
    get_engine_chain_from_env_for_wildcard,
    get_fallback_config_from_env,
)
from content_core.engine_config.resolver import EngineResolver
from content_core.engine_config.schema import ExtractionConfig, FallbackConfig

__all__ = [
    # Schema
    "ExtractionConfig",
    "FallbackConfig",
    # Resolver
    "EngineResolver",
    # ENV parsing
    "get_engine_chain_from_env_for_mime_type",
    "get_engine_chain_from_env_for_wildcard",
    "get_engine_chain_from_env_for_category",
    "get_fallback_config_from_env",
    "MIME_TO_ENV_KEY",
    "CATEGORY_TO_ENV_KEY",
]
