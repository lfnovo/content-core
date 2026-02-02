"""Tests for FallbackExecutor and fallback behavior."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_core.common.exceptions import ExtractionError, FatalExtractionError
from content_core.engine_config.schema import FallbackConfig
from content_core.content.extraction.fallback import FallbackExecutor
from content_core.processors.base import ProcessorResult, Source


class TestFallbackExecutor:
    """Test FallbackExecutor execution logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = FallbackConfig(
            enabled=True,
            max_attempts=3,
            on_error="warn",
            fatal_errors=[
                "FileNotFoundError",
                "PermissionError",
                "FatalExtractionError",
            ],
        )
        self.source = Source(
            file_path="/path/to/test.pdf",
            mime_type="application/pdf",
        )

    @pytest.mark.asyncio
    async def test_successful_first_engine(self):
        """Should return result from first successful engine."""
        executor = FallbackExecutor(self.config)

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = AsyncMock(
            return_value=ProcessorResult(
                content="Test content",
                mime_type="application/pdf",
                metadata={"extraction_engine": "docling"},
            )
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            result = await executor.execute(
                source=self.source,
                engines=["docling", "pymupdf"],
            )

        assert result.content == "Test content"
        assert result.metadata["extraction_engine"] == "docling"
        assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """Should fallback to next engine on failure."""
        executor = FallbackExecutor(self.config)

        # First engine fails, second succeeds
        mock_processor1 = MagicMock()
        mock_processor1.is_available.return_value = True
        mock_processor1.return_value.extract = AsyncMock(
            side_effect=RuntimeError("Engine 1 failed")
        )

        mock_processor2 = MagicMock()
        mock_processor2.is_available.return_value = True
        mock_processor2.return_value.extract = AsyncMock(
            return_value=ProcessorResult(
                content="Content from engine 2",
                mime_type="application/pdf",
                metadata={"extraction_engine": "pymupdf"},
            )
        )

        mock_registry = MagicMock()
        mock_registry.get.side_effect = [mock_processor1, mock_processor2]

        with patch.object(executor, "_registry", mock_registry):
            result = await executor.execute(
                source=self.source,
                engines=["docling", "pymupdf"],
            )

        assert result.content == "Content from engine 2"
        assert "fallback" in result.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_fatal_error_stops_fallback(self):
        """Fatal errors should not trigger fallback."""
        executor = FallbackExecutor(self.config)

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = AsyncMock(
            side_effect=FileNotFoundError("File not found")
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(FatalExtractionError) as exc_info:
                await executor.execute(
                    source=self.source,
                    engines=["docling", "pymupdf"],
                )
            assert "Fatal extraction error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fatal_extraction_error_stops_fallback(self):
        """FatalExtractionError should stop fallback."""
        executor = FallbackExecutor(self.config)

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = AsyncMock(
            side_effect=FatalExtractionError("Cannot process")
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(FatalExtractionError):
                await executor.execute(
                    source=self.source,
                    engines=["docling", "pymupdf"],
                )

    @pytest.mark.asyncio
    async def test_all_engines_fail(self):
        """Should raise ExtractionError when all engines fail."""
        executor = FallbackExecutor(self.config)

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = AsyncMock(
            side_effect=RuntimeError("Engine failed")
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(ExtractionError) as exc_info:
                await executor.execute(
                    source=self.source,
                    engines=["docling", "pymupdf"],
                )
            assert "All 2 engines failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_max_attempts_limit(self):
        """Should respect max_attempts configuration."""
        config = FallbackConfig(
            enabled=True,
            max_attempts=2,
            on_error="warn",
        )
        executor = FallbackExecutor(config)

        call_count = 0

        async def failing_extract(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Failed")

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = failing_extract

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(ExtractionError):
                await executor.execute(
                    source=self.source,
                    engines=["engine1", "engine2", "engine3", "engine4"],
                )

        # Should only try 2 engines despite 4 being available
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_fallback_disabled(self):
        """When fallback disabled, should only try first engine."""
        config = FallbackConfig(
            enabled=False,
            max_attempts=3,
        )
        executor = FallbackExecutor(config)

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = AsyncMock(
            side_effect=RuntimeError("Failed")
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(ExtractionError) as exc_info:
                await executor.execute(
                    source=self.source,
                    engines=["docling", "pymupdf"],
                )
            assert "All 1 engines failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_on_error_fail(self):
        """on_error=fail should raise immediately."""
        config = FallbackConfig(
            enabled=True,
            max_attempts=3,
            on_error="fail",
        )
        executor = FallbackExecutor(config)

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = AsyncMock(
            side_effect=RuntimeError("Failed")
        )

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(ExtractionError) as exc_info:
                await executor.execute(
                    source=self.source,
                    engines=["docling", "pymupdf"],
                )
            assert "docling" in str(exc_info.value)
            assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_engine_not_found(self):
        """Should raise ExtractionError for unknown engine."""
        executor = FallbackExecutor(self.config)

        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        mock_registry.list_names.return_value = ["docling", "pymupdf"]

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(ExtractionError) as exc_info:
                await executor.execute(
                    source=self.source,
                    engines=["unknown-engine"],
                )
            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_engine_not_available(self):
        """Should raise ExtractionError for unavailable engine."""
        executor = FallbackExecutor(self.config)

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = False
        mock_processor.capabilities.requires = ["missing-dep"]

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(ExtractionError) as exc_info:
                await executor.execute(
                    source=self.source,
                    engines=["unavailable-engine"],
                )
            assert "not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Should timeout on slow engines."""
        executor = FallbackExecutor(self.config)

        async def slow_extract(*args, **kwargs):
            await asyncio.sleep(10)
            return ProcessorResult(content="", mime_type="")

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = slow_extract

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            with pytest.raises(ExtractionError):
                await executor.execute(
                    source=self.source,
                    engines=["slow-engine"],
                    timeout=0.1,  # Very short timeout
                )

    @pytest.mark.asyncio
    async def test_engine_options_merged(self):
        """Should merge global and engine-specific options."""
        executor = FallbackExecutor(self.config)

        received_options = None

        async def capture_options(source, options):
            nonlocal received_options
            received_options = options
            return ProcessorResult(
                content="Test",
                mime_type="application/pdf",
            )

        mock_processor = MagicMock()
        mock_processor.is_available.return_value = True
        mock_processor.return_value.extract = capture_options

        mock_registry = MagicMock()
        mock_registry.get.return_value = mock_processor

        with patch.object(executor, "_registry", mock_registry):
            await executor.execute(
                source=self.source,
                engines=["docling"],
                options={"global_opt": True},
                engine_options={
                    "docling": {"engine_opt": "value"},
                },
            )

        assert received_options["global_opt"] is True
        assert received_options["engine_opt"] == "value"


class TestIsFatalError:
    """Test fatal error detection."""

    def test_file_not_found_is_fatal(self):
        """FileNotFoundError should be fatal."""
        executor = FallbackExecutor(
            FallbackConfig(fatal_errors=["FileNotFoundError"])
        )
        assert executor._is_fatal_error(FileNotFoundError("test"))

    def test_permission_error_is_fatal(self):
        """PermissionError should be fatal."""
        executor = FallbackExecutor(
            FallbackConfig(fatal_errors=["PermissionError"])
        )
        assert executor._is_fatal_error(PermissionError("test"))

    def test_fatal_extraction_error_is_fatal(self):
        """FatalExtractionError should always be fatal."""
        executor = FallbackExecutor(FallbackConfig(fatal_errors=[]))
        assert executor._is_fatal_error(FatalExtractionError("test"))

    def test_runtime_error_is_not_fatal(self):
        """RuntimeError should not be fatal by default."""
        executor = FallbackExecutor(
            FallbackConfig(fatal_errors=["FileNotFoundError"])
        )
        assert not executor._is_fatal_error(RuntimeError("test"))

    def test_custom_fatal_errors(self):
        """Should respect custom fatal errors list."""
        executor = FallbackExecutor(
            FallbackConfig(fatal_errors=["ValueError", "TypeError"])
        )
        assert executor._is_fatal_error(ValueError("test"))
        assert executor._is_fatal_error(TypeError("test"))
        assert not executor._is_fatal_error(RuntimeError("test"))
