"""Unit tests for the new extract_content API."""

import os
import tempfile

import pytest

from content_core.common import ExtractionResult, ProcessSourceInput, ProcessSourceOutput
from content_core.common.exceptions import ExtractionError
from content_core.content.extraction import extract_content
from content_core.processors.registry import ProcessorRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset and re-initialize registry before each test."""
    # Ensure processors are imported (only needed once, but safe to call multiple times)
    from content_core import processors  # noqa: F401

    # Reset and reinitialize to get clean state with real processors
    ProcessorRegistry.reset()
    ProcessorRegistry.reinitialize()
    yield


class TestExtractContentValidation:
    """Tests for extract_content input validation."""

    @pytest.mark.asyncio
    async def test_no_source_raises_error(self):
        """Test that calling with no source raises ValueError."""
        with pytest.raises(ValueError, match="Must provide one of"):
            await extract_content()

    @pytest.mark.asyncio
    async def test_multiple_sources_raises_error(self):
        """Test that calling with multiple sources raises ValueError."""
        with pytest.raises(ValueError, match="Must provide only one of"):
            await extract_content(
                url="https://example.com",
                file_path="/path/to/file.txt",
            )

    @pytest.mark.asyncio
    async def test_multiple_sources_with_content_raises_error(self):
        """Test that multiple sources including content raises error."""
        with pytest.raises(ValueError, match="Must provide only one of"):
            await extract_content(
                content="Hello world",
                url="https://example.com",
            )


class TestExtractContentLegacyAPI:
    """Tests for backward compatibility with legacy API."""

    @pytest.mark.asyncio
    async def test_legacy_dict_returns_process_source_output(self):
        """Test that legacy dict API returns ProcessSourceOutput."""
        # Create a simple text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello world")
            temp_path = f.name

        try:
            result = await extract_content({"file_path": temp_path})
            assert isinstance(result, ProcessSourceOutput)
            assert "Hello world" in result.content
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_legacy_process_source_input_returns_process_source_output(self):
        """Test that legacy ProcessSourceInput returns ProcessSourceOutput."""
        # Create a simple text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            result = await extract_content(ProcessSourceInput(file_path=temp_path))
            assert isinstance(result, ProcessSourceOutput)
            assert "Test content" in result.content
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_legacy_dict_with_content(self):
        """Test legacy dict with content field."""
        result = await extract_content({"content": "Raw text content"})
        assert isinstance(result, ProcessSourceOutput)


class TestExtractContentNewAPI:
    """Tests for new extract_content API with named parameters."""

    @pytest.mark.asyncio
    async def test_file_path_returns_extraction_result(self):
        """Test that new API returns ExtractionResult."""
        # Create a simple text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content for new API")
            temp_path = f.name

        try:
            result = await extract_content(file_path=temp_path)
            assert isinstance(result, ExtractionResult)
            assert "Test content for new API" in result.content
            assert result.source_type == "file"
            assert result.engine_used != ""
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_content_param_returns_extraction_result(self):
        """Test content parameter returns ExtractionResult."""
        result = await extract_content(content="Hello world from new API")
        assert isinstance(result, ExtractionResult)
        assert result.source_type == "content"

    @pytest.mark.asyncio
    async def test_with_mime_type(self):
        """Test extraction with explicit MIME type."""
        result = await extract_content(
            content="Plain text content",
            mime_type="text/plain",
        )
        assert isinstance(result, ExtractionResult)
        assert result.mime_type == "text/plain"

    @pytest.mark.asyncio
    async def test_with_specific_engine(self):
        """Test extraction with specific engine."""
        # Create a text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test with engine")
            temp_path = f.name

        try:
            result = await extract_content(file_path=temp_path, engine="text")
            assert isinstance(result, ExtractionResult)
            assert result.engine_used == "text"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_unknown_engine_raises_error(self):
        """Test that unknown engine raises ExtractionError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test")
            temp_path = f.name

        try:
            with pytest.raises(ExtractionError, match="not found"):
                await extract_content(file_path=temp_path, engine="nonexistent-engine")
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_path_object_supported(self):
        """Test that Path objects are supported for file_path."""
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test with Path object")
            temp_path = Path(f.name)

        try:
            result = await extract_content(file_path=temp_path)
            assert isinstance(result, ExtractionResult)
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_bytes_content(self):
        """Test extraction with bytes content."""
        result = await extract_content(content=b"Hello from bytes")
        assert isinstance(result, ExtractionResult)
        assert "Hello from bytes" in result.content

    @pytest.mark.asyncio
    async def test_with_options_dict(self):
        """Test extraction with options dict."""
        result = await extract_content(
            content="Test with options",
            options={"custom_option": "value"},
        )
        assert isinstance(result, ExtractionResult)


class TestExtractionResult:
    """Tests for ExtractionResult model."""

    def test_from_legacy(self):
        """Test creating ExtractionResult from legacy output."""
        legacy = ProcessSourceOutput(
            content="Test content",
            source_type="file",
            identified_type="text/plain",
            metadata={"extraction_engine": "text"},
        )

        result = ExtractionResult.from_legacy(legacy, engine="text")
        assert result.content == "Test content"
        assert result.source_type == "file"
        assert result.mime_type == "text/plain"
        assert result.engine_used == "text"

    def test_default_values(self):
        """Test ExtractionResult default values."""
        result = ExtractionResult()
        assert result.content == ""
        assert result.source_type == ""
        assert result.mime_type is None
        assert result.metadata == {}
        assert result.engine_used == ""
        assert result.warnings == []


class TestProcessorRegistryIntegration:
    """Tests for processor registry integration."""

    def test_text_processor_registered(self):
        """Test that text processor is auto-registered."""
        # Import triggers auto-registration
        from content_core import processors  # noqa: F401

        registry = ProcessorRegistry.instance()
        text_proc = registry.get("text")
        assert text_proc is not None

    def test_find_processors_for_text(self):
        """Test finding processors for text/plain."""
        from content_core import processors  # noqa: F401

        registry = ProcessorRegistry.instance()
        procs = registry.find_for_mime_type("text/plain")
        assert len(procs) > 0
        assert any(p.name == "text" for p in procs)

    def test_list_available_processors(self):
        """Test listing available processors."""
        from content_core import processors  # noqa: F401

        registry = ProcessorRegistry.instance()
        available = registry.list_names()
        # At minimum, text processor should be available
        assert "text" in available


class TestRouterIntegration:
    """Tests for router integration."""

    @pytest.mark.asyncio
    async def test_detect_mime_type_for_file(self):
        """Test MIME type detection for files."""
        from content_core.content.extraction.router import detect_mime_type

        # Create a text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test")
            temp_path = f.name

        try:
            mime = await detect_mime_type(file_path=temp_path)
            assert mime == "text/plain"
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_detect_mime_type_for_content(self):
        """Test MIME type detection for raw content."""
        from content_core.content.extraction.router import detect_mime_type

        # Plain text
        mime = await detect_mime_type(content="Hello world")
        assert mime == "text/plain"

        # HTML-like content
        mime = await detect_mime_type(content="<html><body>Hello</body></html>")
        assert mime == "text/html"

    @pytest.mark.asyncio
    async def test_detect_youtube_url(self):
        """Test YouTube URL detection."""
        from content_core.content.extraction.router import detect_mime_type

        mime = await detect_mime_type(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert mime == "youtube"

        mime = await detect_mime_type(url="https://youtu.be/dQw4w9WgXcQ")
        assert mime == "youtube"

    @pytest.mark.asyncio
    async def test_get_available_engines(self):
        """Test getting available engines."""
        from content_core.content.extraction.router import get_available_engines

        engines = await get_available_engines()
        assert isinstance(engines, dict)
        # At minimum, text processor should be available
        assert "text" in engines
        assert "mime_types" in engines["text"]
        assert "priority" in engines["text"]
