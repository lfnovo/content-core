"""Processor registry for content extraction.

This module provides the ProcessorRegistry class and @processor decorator
for registering and discovering content processors.

Usage:
    from content_core.processors.registry import processor, ProcessorRegistry

    @processor(
        name="my-processor",
        mime_types=["application/pdf"],
        priority=60,
    )
    class MyProcessor(Processor):
        async def extract(self, source, options=None):
            ...

    # Get registry
    registry = ProcessorRegistry.instance()

    # Find processors for a MIME type
    processors = registry.find_for_mime_type("application/pdf")
"""

from typing import Callable, Dict, List, Optional, Type

from content_core.logging import logger
from content_core.processors.base import Processor, ProcessorCapabilities


class ProcessorRegistry:
    """Registry for content processors.

    Singleton registry that manages processor registration and discovery.
    Processors are registered using the @processor decorator or directly
    via the register() method.
    """

    _processors: Dict[str, Type[Processor]] = {}
    _all_processors: List[Type[Processor]] = []  # Track all decorated processors
    _instance: Optional["ProcessorRegistry"] = None

    def __new__(cls) -> "ProcessorRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._processors = {}
        return cls._instance

    @classmethod
    def instance(cls) -> "ProcessorRegistry":
        """Get the singleton registry instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls, clear_all: bool = False) -> None:
        """Reset the registry (primarily for testing).

        Args:
            clear_all: If True, also clears the _all_processors list.
                      This should only be True for tests that want to start fresh.
                      Default is False to allow reinitialize() to work.

        After reset, call reinitialize() to re-register all decorated processors.
        """
        cls._instance = None
        cls._processors = {}
        if clear_all:
            cls._all_processors = []

    @classmethod
    def reinitialize(cls) -> None:
        """Re-register all known processors.

        This is useful after reset() to restore the registry to its initial state.
        """
        registry = cls.instance()
        for processor_cls in cls._all_processors:
            registry.register(processor_cls)

    def register(self, processor_cls: Type[Processor]) -> Type[Processor]:
        """Register a processor class.

        Processors that are not available (is_available() returns False)
        are not registered.

        Args:
            processor_cls: The Processor class to register.

        Returns:
            The same processor class (allows use as decorator).
        """
        if not processor_cls.is_available():
            logger.debug(
                f"Processor '{processor_cls.name}' not available, skipping registration"
            )
            return processor_cls

        if processor_cls.name in self._processors:
            logger.warning(
                f"Processor '{processor_cls.name}' already registered, overwriting"
            )

        self._processors[processor_cls.name] = processor_cls
        logger.debug(
            f"Registered processor '{processor_cls.name}' with priority "
            f"{processor_cls.capabilities.priority}"
        )
        return processor_cls

    def unregister(self, name: str) -> bool:
        """Unregister a processor by name.

        Args:
            name: The processor name to unregister.

        Returns:
            True if the processor was unregistered, False if not found.
        """
        if name in self._processors:
            del self._processors[name]
            return True
        return False

    def get(self, name: str) -> Optional[Type[Processor]]:
        """Get a processor by name.

        Args:
            name: The processor name.

        Returns:
            The Processor class, or None if not found.
        """
        return self._processors.get(name)

    def find_for_mime_type(self, mime_type: str) -> List[Type[Processor]]:
        """Find all processors that support a given MIME type.

        Args:
            mime_type: The MIME type to find processors for.

        Returns:
            List of Processor classes sorted by priority (highest first).
        """
        matching = []
        for processor_cls in self._processors.values():
            if processor_cls.supports_mime_type(mime_type):
                matching.append(processor_cls)

        # Sort by priority (highest first)
        return sorted(
            matching, key=lambda p: p.capabilities.priority, reverse=True
        )

    def find_for_extension(self, extension: str) -> List[Type[Processor]]:
        """Find all processors that support a given file extension.

        Args:
            extension: The file extension (with or without leading dot).

        Returns:
            List of Processor classes sorted by priority (highest first).
        """
        matching = []
        for processor_cls in self._processors.values():
            if processor_cls.supports_extension(extension):
                matching.append(processor_cls)

        # Sort by priority (highest first)
        return sorted(
            matching, key=lambda p: p.capabilities.priority, reverse=True
        )

    def find_for_category(self, category: str) -> List[Type[Processor]]:
        """Find all processors in a given category.

        Args:
            category: The category to filter by (e.g., "documents", "urls").

        Returns:
            List of Processor classes in the category, sorted by priority.
        """
        matching = [
            p
            for p in self._processors.values()
            if p.capabilities.category == category
        ]
        return sorted(
            matching, key=lambda p: p.capabilities.priority, reverse=True
        )

    def list_available(self) -> List[Type[Processor]]:
        """List all available (registered) processors.

        Returns:
            List of all registered Processor classes.
        """
        return list(self._processors.values())

    def list_names(self) -> List[str]:
        """List names of all available processors.

        Returns:
            List of processor names.
        """
        return list(self._processors.keys())


def processor(
    name: str,
    mime_types: List[str],
    priority: int = 50,
    extensions: Optional[List[str]] = None,
    requires: Optional[List[str]] = None,
    category: str = "documents",
    _internal: bool = True,
) -> Callable[[Type[Processor]], Type[Processor]]:
    """Decorator to register a processor class.

    Usage:
        @processor(
            name="docling",
            mime_types=["application/pdf", "image/*"],
            extensions=[".pdf", ".png", ".jpg"],
            priority=60,
            requires=["docling"],
            category="documents",
        )
        class DoclingProcessor(Processor):
            async def extract(self, source, options=None):
                ...

    Args:
        name: Unique identifier for this processor.
        mime_types: List of MIME types this processor can handle.
        priority: Priority for selection (0-100). Higher = preferred.
        extensions: List of file extensions (with leading dot).
        requires: List of optional dependencies required.
        category: Category for grouping.
        _internal: If True, processor is tracked for reinitialize(). Set to False
                   for test processors that shouldn't persist across resets.

    Returns:
        Decorator function that registers the processor.
    """

    def decorator(cls: Type[Processor]) -> Type[Processor]:
        # Set class attributes
        cls.name = name
        cls.capabilities = ProcessorCapabilities(
            mime_types=mime_types,
            extensions=extensions or [],
            priority=priority,
            requires=requires or [],
            category=category,
        )

        # Track internal processors for reinitialize() - not test processors
        if _internal and cls not in ProcessorRegistry._all_processors:
            ProcessorRegistry._all_processors.append(cls)

        # Register with the singleton registry
        ProcessorRegistry.instance().register(cls)

        return cls

    return decorator
