"""Registry-based routing for content extraction.

This module provides the routing logic that uses the processor registry
to find and execute the appropriate processor for a given source.
"""

import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from content_core.logging import logger
from content_core.processors import ProcessorRegistry, Source
from content_core.processors.base import Processor, ProcessorResult


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


def select_processor(
    mime_type: str,
    engine: Optional[Union[str, List[str]]] = None,
) -> Optional[Type[Processor]]:
    """Select the best processor for a given MIME type and engine preference.

    Args:
        mime_type: The MIME type to find a processor for.
        engine: Optional engine name(s). If a list, tries each in order.

    Returns:
        The best matching Processor class, or None if no match found.
    """
    registry = ProcessorRegistry.instance()

    # If specific engine(s) requested, use those
    if engine:
        engines = [engine] if isinstance(engine, str) else engine
        for eng in engines:
            processor_cls = registry.get(eng)
            if processor_cls and processor_cls.is_available():
                # Verify it supports the MIME type (if specified)
                if mime_type and processor_cls.supports_mime_type(mime_type):
                    return processor_cls
                elif not mime_type:
                    return processor_cls
                else:
                    logger.warning(
                        f"Engine '{eng}' doesn't support MIME type '{mime_type}'"
                    )
            else:
                logger.debug(f"Engine '{eng}' not available")
        return None

    # Auto-select based on MIME type
    if mime_type:
        processors = registry.find_for_mime_type(mime_type)
        if processors:
            return processors[0]  # Highest priority

    return None


async def route_and_extract(
    file_path: Optional[Union[str, Path]] = None,
    url: Optional[str] = None,
    content: Optional[Union[str, bytes]] = None,
    mime_type: Optional[str] = None,
    engine: Optional[Union[str, List[str]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> ProcessorResult:
    """Route to the appropriate processor and extract content.

    This is the main entry point for the new extraction API.

    Args:
        file_path: Path to a local file.
        url: URL to fetch content from.
        content: Raw content (string or bytes).
        mime_type: MIME type (detected automatically if not provided).
        engine: Engine name(s) to use. If a list, tries each in order.
        options: Additional processor-specific options.

    Returns:
        ProcessorResult with extracted content.

    Raises:
        ValueError: If no source is provided or no processor is found.
        ImportError: If the required processor dependencies are not installed.
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

    # Select processor
    processor_cls = select_processor(detected_mime, engine)

    if not processor_cls:
        available = ProcessorRegistry.instance().list_names()
        raise ValueError(
            f"No processor found for MIME type '{detected_mime}'. "
            f"Available processors: {available}"
        )

    logger.info(
        f"Using processor '{processor_cls.name}' for MIME type '{detected_mime}'"
    )

    # Create source object
    source = Source(
        file_path=file_path,
        url=url,
        content=content,
        mime_type=detected_mime,
        options=options or {},
    )

    # Instantiate and run processor
    processor = processor_cls()
    result = await processor.extract(source, options)

    # Ensure engine_used is in metadata
    if "extraction_engine" not in result.metadata:
        result.metadata["extraction_engine"] = processor_cls.name

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
