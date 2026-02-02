"""Configuration schema models for content extraction.

This module provides Pydantic models for configuring engine selection
and fallback behavior per MIME type.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class FallbackConfig(BaseModel):
    """Configuration for fallback behavior during extraction.

    Attributes:
        enabled: Whether to enable fallback to next engine on failure.
        max_attempts: Maximum number of engines to try before giving up.
        on_error: How to handle errors. "next" tries next engine silently,
            "warn" logs a warning and tries next, "fail" raises immediately.
        fatal_errors: List of exception class names that should not trigger
            fallback (e.g., FileNotFoundError, PermissionError).
    """

    enabled: bool = True
    max_attempts: int = 3
    on_error: str = "warn"  # "next" | "fail" | "warn"
    fatal_errors: List[str] = Field(
        default_factory=lambda: [
            "FileNotFoundError",
            "PermissionError",
            "ValidationError",
            "FatalExtractionError",
        ]
    )


class ExtractionConfig(BaseModel):
    """Configuration for content extraction.

    Attributes:
        timeout: Default timeout for extraction operations in seconds.
        engines: Engine configuration by MIME type or category.
            Keys can be:
            - Specific MIME types: "application/pdf", "image/png"
            - Wildcard MIME types: "image/*", "audio/*"
            - Categories: "documents", "urls", "audio", "video"
            Values can be a single engine name or list of engines (fallback chain).
        fallback: Fallback configuration for handling engine failures.
        engine_options: Engine-specific options keyed by engine name.
        document_engine: Legacy config - default engine for documents.
        url_engine: Legacy config - default engine for URLs.
    """

    timeout: int = 300
    engines: Dict[str, Union[str, List[str]]] = Field(default_factory=dict)
    fallback: FallbackConfig = Field(default_factory=FallbackConfig)
    engine_options: Dict[str, Dict] = Field(default_factory=dict)
    # Backward compatibility with legacy config
    document_engine: Optional[str] = "auto"
    url_engine: Optional[str] = "auto"

    def get_engines_for_key(self, key: str) -> Optional[List[str]]:
        """Get engine chain for a specific key (MIME type or category).

        Args:
            key: The MIME type or category to look up.

        Returns:
            List of engine names, or None if not configured.
        """
        value = self.engines.get(key)
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        return value

    def get_engine_options(self, engine_name: str) -> Dict:
        """Get options for a specific engine.

        Args:
            engine_name: The engine name to get options for.

        Returns:
            Dict of options, empty if not configured.
        """
        return self.engine_options.get(engine_name, {})
