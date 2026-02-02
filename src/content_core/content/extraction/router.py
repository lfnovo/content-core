"""Registry-based routing for content extraction.

This module provides the routing logic that uses the EngineResolver
and FallbackExecutor to find and execute the appropriate processor(s)
for a given source.
"""

import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from content_core.config import get_extraction_config
from content_core.engine_config.resolver import EngineResolver
from content_core.content.extraction.fallback import FallbackExecutor
from content_core.logging import logger
from content_core.processors import ProcessorRegistry
from content_core.processors.base import ProcessorResult, Source


async def detect_mime_type(
    file_path: Optional[str] = None,
    url: Optional[str] = None,
    content: Optional[Union[str, bytes]] = None,
) -> Optional[str]:
    """Detect MIME type from the source.

    Args:
        file_path: Path to a local file.
        url: URL to fetch content from.
        content: Raw content.

    Returns:
        Detected MIME type or None if unable to detect.
    """
    if file_path:
        # Use file extension to guess MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type

        # Fallback: try to detect from file content using file type detection
        try:
            from content_core.content.identification import get_file_type

            return await get_file_type(file_path)
        except Exception as e:
            logger.debug(f"File type detection failed: {e}")

    if url:
        # Check for YouTube URLs
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"  # Special type for YouTube

        # URL MIME type detection is handled by URL processors
        # Default to HTML for web URLs
        return "text/html"

    if content:
        # For raw content, assume text/plain unless we can detect HTML
        if isinstance(content, str):
            # Simple HTML detection
            if content.strip().startswith("<") and ">" in content:
                return "text/html"
        return "text/plain"

    return None


async def route_and_extract(
    file_path: Optional[Union[str, Path]] = None,
    url: Optional[str] = None,
    content: Optional[Union[str, bytes]] = None,
    mime_type: Optional[str] = None,
    engine: Optional[Union[str, List[str]]] = None,
    options: Optional[Dict[str, Any]] = None,
    timeout: Optional[int] = None,
) -> ProcessorResult:
    """Route to the appropriate processor and extract content.

    This is the main entry point for the new extraction API. It uses
    the EngineResolver to determine which engines to use and the
    FallbackExecutor to handle the extraction with fallback support.

    Args:
        file_path: Path to a local file.
        url: URL to fetch content from.
        content: Raw content (string or bytes).
        mime_type: MIME type (detected automatically if not provided).
        engine: Engine name(s) to use. If provided, overrides config.
        options: Additional processor-specific options.
        timeout: Timeout in seconds (uses config default if not provided).

    Returns:
        ProcessorResult with extracted content.

    Raises:
        ValueError: If no source is provided or no processor is found.
        ExtractionError: If all engines fail.
        FatalExtractionError: If a fatal error occurs.
    """
    # Validate inputs
    sources = [file_path, url, content]
    provided = [s for s in sources if s is not None]
    if len(provided) == 0:
        raise ValueError("Must provide one of: file_path, url, content")
    if len(provided) > 1:
        raise ValueError("Must provide only one of: file_path, url, content")

    # Normalize file_path
    if file_path is not None and isinstance(file_path, Path):
        file_path = str(file_path)

    # Detect MIME type if not provided
    detected_mime = mime_type
    if not detected_mime:
        detected_mime = await detect_mime_type(file_path, url, content)
        logger.debug(f"Detected MIME type: {detected_mime}")

    # Special handling for YouTube URLs
    if url and ("youtube.com" in url or "youtu.be" in url):
        detected_mime = "youtube"

    if not detected_mime:
        raise ValueError(
            "Could not detect MIME type. Please provide mime_type parameter."
        )

    # Get configuration
    config = get_extraction_config()
    effective_timeout = timeout if timeout is not None else config.timeout

    # Resolve engines
    resolver = EngineResolver(config)
    engines = resolver.resolve(detected_mime, explicit=engine)

    logger.info(
        f"Resolved engines for MIME type '{detected_mime}': {engines}"
    )

    # Create source object
    source = Source(
        file_path=file_path,
        url=url,
        content=content,
        mime_type=detected_mime,
        options=options or {},
    )

    # Execute with fallback
    executor = FallbackExecutor(config.fallback)
    result = await executor.execute(
        source=source,
        engines=engines,
        options=options,
        engine_options={
            name: resolver.get_engine_options(name) for name in engines
        },
        timeout=effective_timeout,
    )

    return result


async def get_available_engines() -> Dict[str, Dict[str, Any]]:
    """Get information about all available extraction engines.

    Returns:
        Dictionary mapping engine names to their capabilities.
    """
    registry = ProcessorRegistry.instance()
    engines = {}

    for processor_cls in registry.list_available():
        engines[processor_cls.name] = {
            "mime_types": processor_cls.capabilities.mime_types,
            "extensions": processor_cls.capabilities.extensions,
            "priority": processor_cls.capabilities.priority,
            "category": processor_cls.capabilities.category,
            "requires": processor_cls.capabilities.requires,
            "available": processor_cls.is_available(),
        }

    return engines
