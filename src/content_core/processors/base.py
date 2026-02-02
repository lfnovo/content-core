"""Base classes for content processors.

This module provides the foundation for the processor registry system:
- ProcessorCapabilities: Declares what a processor can handle
- ProcessorResult: Standardized result from all processors
- Source: Unified input representation
- Processor: Abstract base class for all content processors
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Union


@dataclass
class ProcessorCapabilities:
    """Declares what a processor can handle.

    Attributes:
        mime_types: List of MIME types this processor can handle.
            Supports wildcards like "image/*" for matching any image type.
        extensions: List of file extensions (with leading dot) this processor handles.
        priority: Priority for processor selection (0-100). Higher = preferred.
            Used when multiple processors can handle the same MIME type.
        requires: List of optional dependencies required by this processor.
        category: Category for grouping (documents, urls, audio, video, etc.)
    """

    mime_types: List[str]
    extensions: List[str] = field(default_factory=list)
    priority: int = 50
    requires: List[str] = field(default_factory=list)
    category: str = "documents"


@dataclass
class ProcessorResult:
    """Standardized result from all processors.

    Attributes:
        content: The extracted content as a string.
        mime_type: The MIME type of the source that was processed.
        metadata: Additional metadata about the extraction (engine used, etc.)
        warnings: Any warnings that occurred during extraction.
    """

    content: str
    mime_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class Source:
    """Unified source representation for content extraction.

    Exactly one of file_path, url, or content must be provided.

    Attributes:
        file_path: Path to a local file.
        url: URL to fetch content from.
        content: Raw content (string or bytes).
        mime_type: MIME type of the content (may be detected automatically).
        options: Additional processor-specific options.
    """

    file_path: Optional[Union[str, Path]] = None
    url: Optional[str] = None
    content: Optional[Union[str, bytes]] = None
    mime_type: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate that exactly one source is provided."""
        sources = [self.file_path, self.url, self.content]
        provided = [s for s in sources if s is not None]
        if len(provided) == 0:
            raise ValueError("Must provide one of: file_path, url, content")
        if len(provided) > 1:
            raise ValueError("Must provide only one of: file_path, url, content")

        # Normalize file_path to string
        if self.file_path is not None and isinstance(self.file_path, Path):
            self.file_path = str(self.file_path)

    @property
    def source_type(self) -> str:
        """Return the type of source: 'file', 'url', or 'content'."""
        if self.file_path is not None:
            return "file"
        if self.url is not None:
            return "url"
        return "content"


class Processor(ABC):
    """Abstract base class for all content processors.

    Processors extract content from various sources (files, URLs, raw content)
    and return standardized results.

    Class Attributes:
        name: Unique identifier for this processor.
        capabilities: ProcessorCapabilities describing what this processor handles.

    Subclasses should:
    1. Define name and capabilities as class attributes
    2. Implement extract() method
    3. Optionally override is_available() if the processor has optional dependencies
    """

    name: ClassVar[str]
    capabilities: ClassVar[ProcessorCapabilities]

    @abstractmethod
    async def extract(
        self, source: Source, options: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Extract content from the given source.

        Args:
            source: The Source to extract content from.
            options: Optional processor-specific options that override defaults.

        Returns:
            ProcessorResult with the extracted content and metadata.

        Raises:
            ValueError: If the source type is not supported by this processor.
            ImportError: If required dependencies are not available.
        """
        pass

    @classmethod
    def is_available(cls) -> bool:
        """Check if this processor is available (dependencies installed).

        Override this method to check for optional dependencies.

        Returns:
            True if the processor can be used, False otherwise.
        """
        return True

    @classmethod
    def supports_mime_type(cls, mime_type: str) -> bool:
        """Check if this processor supports the given MIME type.

        Supports wildcard matching (e.g., "image/*" matches "image/png").

        Args:
            mime_type: The MIME type to check.

        Returns:
            True if this processor can handle the MIME type.
        """
        import fnmatch

        for pattern in cls.capabilities.mime_types:
            if fnmatch.fnmatch(mime_type, pattern):
                return True
        return False

    @classmethod
    def supports_extension(cls, extension: str) -> bool:
        """Check if this processor supports the given file extension.

        Args:
            extension: The file extension (with or without leading dot).

        Returns:
            True if this processor can handle the extension.
        """
        # Normalize extension to have leading dot
        if not extension.startswith("."):
            extension = f".{extension}"
        return extension.lower() in [e.lower() for e in cls.capabilities.extensions]
