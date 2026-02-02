"""Unit tests for the processor registry."""

import pytest

from content_core.processors.base import (
    Processor,
    ProcessorCapabilities,
    ProcessorResult,
    Source,
)
from content_core.processors.registry import ProcessorRegistry, processor


class TestProcessorCapabilities:
    """Tests for ProcessorCapabilities dataclass."""

    def test_basic_capabilities(self):
        """Test creating basic capabilities."""
        caps = ProcessorCapabilities(
            mime_types=["application/pdf"],
            extensions=[".pdf"],
            priority=50,
        )
        assert caps.mime_types == ["application/pdf"]
        assert caps.extensions == [".pdf"]
        assert caps.priority == 50
        assert caps.requires == []
        assert caps.category == "documents"

    def test_full_capabilities(self):
        """Test creating full capabilities with all fields."""
        caps = ProcessorCapabilities(
            mime_types=["application/pdf", "image/*"],
            extensions=[".pdf", ".png"],
            priority=70,
            requires=["docling"],
            category="vlm",
        )
        assert caps.mime_types == ["application/pdf", "image/*"]
        assert caps.priority == 70
        assert caps.requires == ["docling"]
        assert caps.category == "vlm"


class TestProcessorResult:
    """Tests for ProcessorResult dataclass."""

    def test_basic_result(self):
        """Test creating basic result."""
        result = ProcessorResult(
            content="Hello world",
            mime_type="text/plain",
        )
        assert result.content == "Hello world"
        assert result.mime_type == "text/plain"
        assert result.metadata == {}
        assert result.warnings == []

    def test_full_result(self):
        """Test creating result with all fields."""
        result = ProcessorResult(
            content="Content",
            mime_type="application/pdf",
            metadata={"engine": "docling"},
            warnings=["Warning 1"],
        )
        assert result.metadata == {"engine": "docling"}
        assert result.warnings == ["Warning 1"]


class TestSource:
    """Tests for Source dataclass."""

    def test_file_path_source(self):
        """Test creating source with file path."""
        source = Source(file_path="/path/to/file.pdf")
        assert source.file_path == "/path/to/file.pdf"
        assert source.url is None
        assert source.content is None
        assert source.source_type == "file"

    def test_url_source(self):
        """Test creating source with URL."""
        source = Source(url="https://example.com/doc.pdf")
        assert source.url == "https://example.com/doc.pdf"
        assert source.file_path is None
        assert source.source_type == "url"

    def test_content_source(self):
        """Test creating source with raw content."""
        source = Source(content="Hello world")
        assert source.content == "Hello world"
        assert source.source_type == "content"

    def test_no_source_raises(self):
        """Test that no source raises ValueError."""
        with pytest.raises(ValueError, match="Must provide one of"):
            Source()

    def test_multiple_sources_raises(self):
        """Test that multiple sources raises ValueError."""
        with pytest.raises(ValueError, match="Must provide only one of"):
            Source(file_path="/path/to/file.pdf", url="https://example.com")

    def test_source_with_options(self):
        """Test creating source with options."""
        source = Source(
            file_path="/path/to/file.pdf",
            mime_type="application/pdf",
            options={"output_format": "html"},
        )
        assert source.mime_type == "application/pdf"
        assert source.options == {"output_format": "html"}


class TestProcessorRegistry:
    """Tests for ProcessorRegistry."""

    def setup_method(self):
        """Reset registry before each test (keeps _all_processors for reinitialize)."""
        ProcessorRegistry.reset()

    def test_singleton(self):
        """Test that registry is a singleton."""
        registry1 = ProcessorRegistry.instance()
        registry2 = ProcessorRegistry.instance()
        assert registry1 is registry2

    def test_register_processor(self):
        """Test registering a processor."""

        class TestProcessor(Processor):
            name = "test-processor"
            capabilities = ProcessorCapabilities(
                mime_types=["text/plain"],
                priority=50,
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="test", mime_type="text/plain")

        registry = ProcessorRegistry.instance()
        registry.register(TestProcessor)

        assert registry.get("test-processor") is TestProcessor

    def test_register_unavailable_processor(self):
        """Test that unavailable processors are not registered."""

        class UnavailableProcessor(Processor):
            name = "unavailable"
            capabilities = ProcessorCapabilities(
                mime_types=["text/plain"],
            )

            @classmethod
            def is_available(cls):
                return False

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="text/plain")

        registry = ProcessorRegistry.instance()
        registry.register(UnavailableProcessor)

        assert registry.get("unavailable") is None

    def test_find_for_mime_type(self):
        """Test finding processors by MIME type."""

        class HighPriorityProcessor(Processor):
            name = "high-priority"
            capabilities = ProcessorCapabilities(
                mime_types=["application/pdf"],
                priority=70,
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="application/pdf")

        class LowPriorityProcessor(Processor):
            name = "low-priority"
            capabilities = ProcessorCapabilities(
                mime_types=["application/pdf"],
                priority=30,
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="application/pdf")

        registry = ProcessorRegistry.instance()
        registry.register(HighPriorityProcessor)
        registry.register(LowPriorityProcessor)

        processors = registry.find_for_mime_type("application/pdf")
        assert len(processors) == 2
        assert processors[0] is HighPriorityProcessor  # Higher priority first
        assert processors[1] is LowPriorityProcessor

    def test_find_for_mime_type_with_wildcard(self):
        """Test finding processors with wildcard MIME types."""

        class ImageProcessor(Processor):
            name = "image-processor"
            capabilities = ProcessorCapabilities(
                mime_types=["image/*"],
                priority=50,
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="image/png")

        registry = ProcessorRegistry.instance()
        registry.register(ImageProcessor)

        processors = registry.find_for_mime_type("image/png")
        assert len(processors) == 1
        assert processors[0] is ImageProcessor

        processors = registry.find_for_mime_type("image/jpeg")
        assert len(processors) == 1

    def test_find_for_extension(self):
        """Test finding processors by file extension."""

        class PDFProcessor(Processor):
            name = "pdf-processor"
            capabilities = ProcessorCapabilities(
                mime_types=["application/pdf"],
                extensions=[".pdf"],
                priority=50,
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="application/pdf")

        registry = ProcessorRegistry.instance()
        registry.register(PDFProcessor)

        # Test with dot
        processors = registry.find_for_extension(".pdf")
        assert len(processors) == 1

        # Test without dot
        processors = registry.find_for_extension("pdf")
        assert len(processors) == 1

    def test_find_for_category(self):
        """Test finding processors by category."""

        class DocProcessor(Processor):
            name = "doc-processor"
            capabilities = ProcessorCapabilities(
                mime_types=["application/pdf"],
                category="documents",
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="application/pdf")

        class UrlProcessor(Processor):
            name = "url-processor"
            capabilities = ProcessorCapabilities(
                mime_types=["text/html"],
                category="urls",
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="text/html")

        registry = ProcessorRegistry.instance()
        registry.register(DocProcessor)
        registry.register(UrlProcessor)

        doc_processors = registry.find_for_category("documents")
        assert len(doc_processors) == 1
        assert doc_processors[0] is DocProcessor

        url_processors = registry.find_for_category("urls")
        assert len(url_processors) == 1

    def test_list_available(self):
        """Test listing all available processors."""

        class Processor1(Processor):
            name = "processor-1"
            capabilities = ProcessorCapabilities(mime_types=["text/plain"])

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="text/plain")

        class Processor2(Processor):
            name = "processor-2"
            capabilities = ProcessorCapabilities(mime_types=["text/html"])

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="text/html")

        registry = ProcessorRegistry.instance()
        registry.register(Processor1)
        registry.register(Processor2)

        available = registry.list_available()
        assert len(available) == 2

        names = registry.list_names()
        assert set(names) == {"processor-1", "processor-2"}

    def test_unregister(self):
        """Test unregistering a processor."""

        class TestProcessor(Processor):
            name = "to-unregister"
            capabilities = ProcessorCapabilities(mime_types=["text/plain"])

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="text/plain")

        registry = ProcessorRegistry.instance()
        registry.register(TestProcessor)
        assert registry.get("to-unregister") is not None

        result = registry.unregister("to-unregister")
        assert result is True
        assert registry.get("to-unregister") is None

        # Unregister non-existent
        result = registry.unregister("non-existent")
        assert result is False


class TestProcessorDecorator:
    """Tests for the @processor decorator."""

    def setup_method(self):
        """Reset registry before each test (keeps _all_processors for reinitialize)."""
        ProcessorRegistry.reset()

    def test_decorator_registers_processor(self):
        """Test that decorator registers the processor."""

        @processor(
            name="decorated-processor",
            mime_types=["text/plain"],
            priority=60,
            _internal=False,  # Don't track test processors
        )
        class DecoratedProcessor(Processor):
            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="text/plain")

        registry = ProcessorRegistry.instance()
        assert registry.get("decorated-processor") is DecoratedProcessor
        assert DecoratedProcessor.name == "decorated-processor"
        assert DecoratedProcessor.capabilities.priority == 60

    def test_decorator_with_all_options(self):
        """Test decorator with all options."""

        @processor(
            name="full-processor",
            mime_types=["application/pdf", "image/*"],
            extensions=[".pdf", ".png"],
            priority=70,
            requires=["docling"],
            category="vlm",
            _internal=False,  # Don't track test processors
        )
        class FullProcessor(Processor):
            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="application/pdf")

        assert FullProcessor.capabilities.mime_types == ["application/pdf", "image/*"]
        assert FullProcessor.capabilities.extensions == [".pdf", ".png"]
        assert FullProcessor.capabilities.priority == 70
        assert FullProcessor.capabilities.requires == ["docling"]
        assert FullProcessor.capabilities.category == "vlm"


class TestProcessorBaseClass:
    """Tests for Processor base class methods."""

    def test_supports_mime_type(self):
        """Test supports_mime_type method."""

        class TestProcessor(Processor):
            name = "test"
            capabilities = ProcessorCapabilities(
                mime_types=["application/pdf", "image/*"],
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="application/pdf")

        assert TestProcessor.supports_mime_type("application/pdf") is True
        assert TestProcessor.supports_mime_type("image/png") is True
        assert TestProcessor.supports_mime_type("image/jpeg") is True
        assert TestProcessor.supports_mime_type("text/plain") is False

    def test_supports_extension(self):
        """Test supports_extension method."""

        class TestProcessor(Processor):
            name = "test"
            capabilities = ProcessorCapabilities(
                mime_types=["application/pdf"],
                extensions=[".pdf", ".PDF"],
            )

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="application/pdf")

        assert TestProcessor.supports_extension(".pdf") is True
        assert TestProcessor.supports_extension("pdf") is True  # Without dot
        assert TestProcessor.supports_extension(".PDF") is True  # Case variations
        assert TestProcessor.supports_extension(".txt") is False

    def test_is_available_default(self):
        """Test default is_available returns True."""

        class TestProcessor(Processor):
            name = "test"
            capabilities = ProcessorCapabilities(mime_types=["text/plain"])

            async def extract(self, source, options=None):
                return ProcessorResult(content="", mime_type="text/plain")

        assert TestProcessor.is_available() is True
