"""Engine resolver for content extraction.

This module provides the EngineResolver class that determines which
engine(s) to use for content extraction based on the resolution order:

1. Explicit engine param in extract_content() call
2. ENV var for specific MIME type (CCORE_ENGINE_APPLICATION_PDF)
3. YAML config for specific MIME type
4. ENV var for wildcard MIME type (CCORE_ENGINE_IMAGE)
5. YAML config for wildcard MIME type
6. ENV var for category (CCORE_ENGINE_DOCUMENTS)
7. YAML config for category
8. Legacy config (document_engine/url_engine for backward compat)
9. Auto-detect (highest priority available processor from registry)
"""

import fnmatch
from typing import List, Optional, Union

from content_core.engine_config.env import (
    get_engine_chain_from_env_for_category,
    get_engine_chain_from_env_for_mime_type,
    get_engine_chain_from_env_for_wildcard,
)
from content_core.engine_config.schema import ExtractionConfig
from content_core.logging import logger
from content_core.processors import ProcessorRegistry


# Mapping from MIME types to categories
MIME_TYPE_TO_CATEGORY = {
    "application/pdf": "documents",
    "application/epub+zip": "documents",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "documents",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "documents",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "documents",
    "application/msword": "documents",
    "text/html": "urls",
    "text/plain": "text",
    "text/markdown": "text",
    "youtube": "urls",
}

# Wildcard MIME types to categories
WILDCARD_MIME_TO_CATEGORY = {
    "image/*": "documents",  # Images are processed as documents
    "audio/*": "audio",
    "video/*": "video",
    "text/*": "text",
}


def _get_category_for_mime_type(mime_type: str) -> Optional[str]:
    """Get the category for a MIME type.

    Args:
        mime_type: The MIME type (e.g., "application/pdf", "image/png").

    Returns:
        The category name, or None if unknown.
    """
    # Check exact match first
    if mime_type in MIME_TYPE_TO_CATEGORY:
        return MIME_TYPE_TO_CATEGORY[mime_type]

    # Check wildcard patterns
    for pattern, category in WILDCARD_MIME_TO_CATEGORY.items():
        if fnmatch.fnmatch(mime_type, pattern):
            return category

    return None


def _get_wildcard_mime_type(mime_type: str) -> Optional[str]:
    """Get the wildcard pattern for a MIME type.

    Args:
        mime_type: The MIME type (e.g., "image/png").

    Returns:
        The wildcard pattern (e.g., "image/*"), or None.
    """
    if "/" not in mime_type:
        return None
    main_type = mime_type.split("/")[0]
    return f"{main_type}/*"


class EngineResolver:
    """Resolves which engine(s) to use for content extraction.

    This class implements the resolution order to determine the engine
    chain based on configuration hierarchy.
    """

    def __init__(self, config: ExtractionConfig):
        """Initialize the resolver.

        Args:
            config: The extraction configuration.
        """
        self.config = config
        self._registry: Optional[ProcessorRegistry] = None

    @property
    def registry(self) -> ProcessorRegistry:
        """Get the processor registry (lazy loaded)."""
        if self._registry is None:
            self._registry = ProcessorRegistry.instance()
        return self._registry

    def resolve(
        self,
        mime_type: str,
        explicit: Optional[Union[str, List[str]]] = None,
        category: Optional[str] = None,
    ) -> List[str]:
        """Resolve engine chain following resolution order.

        Args:
            mime_type: The MIME type of the content to extract.
            explicit: Explicit engine(s) from extract_content() call.
            category: Optional category override.

        Returns:
            List of engine names to try, in order.

        Raises:
            ValueError: If no engines can be resolved.
        """
        # 1. Explicit param
        if explicit:
            engines = [explicit] if isinstance(explicit, str) else explicit
            logger.debug(f"Using explicit engines: {engines}")
            return engines

        # 2. ENV var for specific MIME type
        engines = get_engine_chain_from_env_for_mime_type(mime_type)
        if engines:
            logger.debug(f"Using ENV engines for MIME type '{mime_type}': {engines}")
            return engines

        # 3. YAML config for specific MIME type
        engines = self.config.get_engines_for_key(mime_type)
        if engines:
            logger.debug(f"Using YAML engines for MIME type '{mime_type}': {engines}")
            return engines

        # 4. ENV var for wildcard MIME type
        wildcard = _get_wildcard_mime_type(mime_type)
        if wildcard:
            engines = get_engine_chain_from_env_for_wildcard(mime_type)
            if engines:
                logger.debug(f"Using ENV engines for wildcard '{wildcard}': {engines}")
                return engines

            # 5. YAML config for wildcard MIME type
            engines = self.config.get_engines_for_key(wildcard)
            if engines:
                logger.debug(
                    f"Using YAML engines for wildcard '{wildcard}': {engines}"
                )
                return engines

        # Determine category if not provided
        resolved_category = category or _get_category_for_mime_type(mime_type)

        if resolved_category:
            # 6. ENV var for category
            engines = get_engine_chain_from_env_for_category(resolved_category)
            if engines:
                logger.debug(
                    f"Using ENV engines for category '{resolved_category}': {engines}"
                )
                return engines

            # 7. YAML config for category
            engines = self.config.get_engines_for_key(resolved_category)
            if engines:
                logger.debug(
                    f"Using YAML engines for category '{resolved_category}': {engines}"
                )
                return engines

        # 8. Legacy config (document_engine/url_engine)
        legacy_engine = self._get_legacy_engine(mime_type, resolved_category)
        if legacy_engine and legacy_engine != "auto":
            logger.debug(f"Using legacy engine: {legacy_engine}")
            return [legacy_engine]

        # 9. Auto-detect from registry
        engines = self._auto_detect_engines(mime_type)
        if engines:
            logger.debug(f"Auto-detected engines for '{mime_type}': {engines}")
            return engines

        raise ValueError(
            f"No engines available for MIME type '{mime_type}'. "
            f"Available processors: {self.registry.list_names()}"
        )

    def _get_legacy_engine(
        self, mime_type: str, category: Optional[str]
    ) -> Optional[str]:
        """Get engine from legacy config (document_engine/url_engine).

        Args:
            mime_type: The MIME type.
            category: The resolved category.

        Returns:
            The legacy engine name, or None.
        """
        # URLs use url_engine
        if category == "urls" or mime_type == "text/html" or mime_type == "youtube":
            return self.config.url_engine

        # Everything else uses document_engine
        return self.config.document_engine

    def _auto_detect_engines(self, mime_type: str) -> List[str]:
        """Auto-detect engines from the processor registry.

        Args:
            mime_type: The MIME type to find processors for.

        Returns:
            List of engine names sorted by priority.
        """
        processors = self.registry.find_for_mime_type(mime_type)
        return [p.name for p in processors if p.is_available()]

    def get_engine_options(self, engine_name: str) -> dict:
        """Get options for a specific engine.

        Args:
            engine_name: The engine name.

        Returns:
            Dict of engine options.
        """
        return self.config.get_engine_options(engine_name)
