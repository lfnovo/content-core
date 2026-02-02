"""Content processors for various file types and sources.

This module provides:
- Base classes for processors (Processor, ProcessorCapabilities, ProcessorResult, Source)
- ProcessorRegistry for discovering and selecting processors
- @processor decorator for registering new processors

Processors are automatically registered when imported. The registry handles:
- MIME type based routing
- Priority-based selection when multiple processors support the same type
- Availability checking for optional dependencies

Usage:
    from content_core.processors import ProcessorRegistry, Source

    # Get registry
    registry = ProcessorRegistry.instance()

    # Find processors for a file type
    processors = registry.find_for_mime_type("application/pdf")

    # Use the highest priority available processor
    if processors:
        proc = processors[0]()
        source = Source(file_path="/path/to/file.pdf", mime_type="application/pdf")
        result = await proc.extract(source)
"""

from content_core.logging import logger

# Export base classes and registry
from content_core.processors.base import (
    Processor,
    ProcessorCapabilities,
    ProcessorResult,
    Source,
)
from content_core.processors.registry import ProcessorRegistry, processor

# =============================================================================
# Auto-discovery: Import all processor modules to trigger registration
# =============================================================================

# Document processors
try:
    from content_core.processors import docling  # noqa: F401
except ImportError as e:
    logger.debug(f"Docling processor not available: {e}")

try:
    from content_core.processors import docling_vlm  # noqa: F401
except ImportError as e:
    logger.debug(f"Docling VLM processor not available: {e}")

try:
    from content_core.processors import marker  # noqa: F401
except ImportError as e:
    logger.debug(f"Marker processor not available: {e}")

try:
    from content_core.processors import pdf  # noqa: F401
except ImportError as e:
    logger.debug(f"PyMuPDF processor not available: {e}")

try:
    from content_core.processors import pdf_llm  # noqa: F401
except ImportError as e:
    logger.debug(f"PyMuPDF4LLM processor not available: {e}")

try:
    from content_core.processors import office  # noqa: F401
except ImportError as e:
    logger.debug(f"Office processor not available: {e}")

try:
    from content_core.processors import text  # noqa: F401
except ImportError as e:
    logger.debug(f"Text processor not available: {e}")

# URL processors
try:
    from content_core.processors import url  # noqa: F401
except ImportError as e:
    logger.debug(f"URL processors not available: {e}")

try:
    from content_core.processors import youtube  # noqa: F401
except ImportError as e:
    logger.debug(f"YouTube processor not available: {e}")

# Audio/Video processors
try:
    from content_core.processors import audio  # noqa: F401
except ImportError as e:
    logger.debug(f"Audio processor not available: {e}")

try:
    from content_core.processors import video  # noqa: F401
except ImportError as e:
    logger.debug(f"Video processor not available: {e}")


__all__ = [
    # Base classes
    "Processor",
    "ProcessorCapabilities",
    "ProcessorResult",
    "Source",
    # Registry
    "ProcessorRegistry",
    "processor",
]
