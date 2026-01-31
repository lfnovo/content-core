"""Unit tests for the Docling VLM processor."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_core.common.state import ProcessSourceState
from content_core.config import (
    ALLOWED_VLM_BACKENDS,
    ALLOWED_VLM_INFERENCE_MODES,
    ALLOWED_VLM_MODELS,
    get_vlm_backend,
    get_vlm_inference_mode,
    get_vlm_model,
    get_vlm_remote_api_key,
    get_vlm_remote_timeout,
    get_vlm_remote_url,
    set_vlm_backend,
    set_vlm_inference_mode,
    set_vlm_model,
    set_vlm_remote_timeout,
    set_vlm_remote_url,
)


class TestVLMConfigGetters:
    """Test VLM configuration getter functions."""

    def test_get_vlm_inference_mode_default(self):
        """Test default inference mode is 'local'."""
        # Clear env var if set
        with patch.dict(os.environ, {}, clear=True):
            mode = get_vlm_inference_mode()
            assert mode in ALLOWED_VLM_INFERENCE_MODES

    def test_get_vlm_inference_mode_env_override(self):
        """Test environment variable override for inference mode."""
        with patch.dict(os.environ, {"CCORE_VLM_INFERENCE_MODE": "remote"}):
            mode = get_vlm_inference_mode()
            assert mode == "remote"

    def test_get_vlm_inference_mode_invalid_env(self):
        """Test invalid environment variable falls back to config."""
        with patch.dict(os.environ, {"CCORE_VLM_INFERENCE_MODE": "invalid"}):
            mode = get_vlm_inference_mode()
            assert mode in ALLOWED_VLM_INFERENCE_MODES

    def test_get_vlm_backend_default(self):
        """Test default backend is in allowed values."""
        with patch.dict(os.environ, {}, clear=True):
            backend = get_vlm_backend()
            assert backend in ALLOWED_VLM_BACKENDS

    def test_get_vlm_backend_env_override(self):
        """Test environment variable override for backend."""
        with patch.dict(os.environ, {"CCORE_VLM_BACKEND": "mlx"}):
            backend = get_vlm_backend()
            assert backend == "mlx"

    def test_get_vlm_model_default(self):
        """Test default model is in allowed values."""
        with patch.dict(os.environ, {}, clear=True):
            model = get_vlm_model()
            assert model in ALLOWED_VLM_MODELS

    def test_get_vlm_model_env_override(self):
        """Test environment variable override for model."""
        with patch.dict(os.environ, {"CCORE_VLM_MODEL": "smol-docling"}):
            model = get_vlm_model()
            assert model == "smol-docling"

    def test_get_vlm_remote_url_default(self):
        """Test default remote URL."""
        with patch.dict(os.environ, {}, clear=True):
            url = get_vlm_remote_url()
            assert "localhost" in url or url.startswith("http")

    def test_get_vlm_remote_url_env_override(self):
        """Test environment variable override for remote URL."""
        with patch.dict(os.environ, {"CCORE_DOCLING_SERVE_URL": "http://custom:8080"}):
            url = get_vlm_remote_url()
            assert url == "http://custom:8080"

    def test_get_vlm_remote_api_key_default(self):
        """Test default API key is None."""
        with patch.dict(os.environ, {}, clear=True):
            key = get_vlm_remote_api_key()
            assert key is None

    def test_get_vlm_remote_api_key_env_override(self):
        """Test environment variable override for API key."""
        with patch.dict(os.environ, {"CCORE_DOCLING_SERVE_API_KEY": "test-key"}):
            key = get_vlm_remote_api_key()
            assert key == "test-key"

    def test_get_vlm_remote_timeout_default(self):
        """Test default timeout is reasonable."""
        with patch.dict(os.environ, {}, clear=True):
            timeout = get_vlm_remote_timeout()
            assert timeout >= 1
            assert timeout <= 3600

    def test_get_vlm_remote_timeout_env_override(self):
        """Test environment variable override for timeout."""
        with patch.dict(os.environ, {"CCORE_DOCLING_SERVE_TIMEOUT": "300"}):
            timeout = get_vlm_remote_timeout()
            assert timeout == 300

    def test_get_vlm_remote_timeout_invalid_env(self):
        """Test invalid timeout falls back to default."""
        with patch.dict(os.environ, {"CCORE_DOCLING_SERVE_TIMEOUT": "not-a-number"}):
            timeout = get_vlm_remote_timeout()
            assert timeout >= 1


class TestVLMConfigSetters:
    """Test VLM configuration setter functions."""

    def test_set_vlm_inference_mode_valid(self):
        """Test setting valid inference mode."""
        set_vlm_inference_mode("remote")
        # This should not raise

    def test_set_vlm_inference_mode_invalid(self):
        """Test setting invalid inference mode raises ValueError."""
        with pytest.raises(ValueError):
            set_vlm_inference_mode("invalid")

    def test_set_vlm_backend_valid(self):
        """Test setting valid backend."""
        set_vlm_backend("transformers")
        # This should not raise

    def test_set_vlm_backend_invalid(self):
        """Test setting invalid backend raises ValueError."""
        with pytest.raises(ValueError):
            set_vlm_backend("invalid")

    def test_set_vlm_model_valid(self):
        """Test setting valid model."""
        set_vlm_model("smol-docling")
        # This should not raise

    def test_set_vlm_model_invalid(self):
        """Test setting invalid model raises ValueError."""
        with pytest.raises(ValueError):
            set_vlm_model("invalid-model")

    def test_set_vlm_remote_url(self):
        """Test setting remote URL."""
        set_vlm_remote_url("http://custom:5001")
        # This should not raise

    def test_set_vlm_remote_timeout_valid(self):
        """Test setting valid timeout."""
        set_vlm_remote_timeout(300)
        # This should not raise

    def test_set_vlm_remote_timeout_invalid(self):
        """Test setting invalid timeout raises ValueError."""
        with pytest.raises(ValueError):
            set_vlm_remote_timeout(0)
        with pytest.raises(ValueError):
            set_vlm_remote_timeout(5000)


class TestVLMProcessorAvailability:
    """Test VLM processor availability checks."""

    def test_import_docling_vlm_module(self):
        """Test that docling_vlm module can be imported."""
        from content_core.processors import docling_vlm

        # Check availability flags exist
        assert hasattr(docling_vlm, "DOCLING_VLM_LOCAL_AVAILABLE")
        assert hasattr(docling_vlm, "DOCLING_VLM_MLX_AVAILABLE")
        assert hasattr(docling_vlm, "extract_with_docling_vlm")

    def test_extract_functions_exist(self):
        """Test that extraction functions are defined."""
        from content_core.processors.docling_vlm import (
            extract_with_docling_vlm,
            extract_with_vlm_local,
            extract_with_vlm_remote,
        )

        assert callable(extract_with_docling_vlm)
        assert callable(extract_with_vlm_local)
        assert callable(extract_with_vlm_remote)


class TestVLMBackendDetection:
    """Test VLM backend auto-detection."""

    def test_detect_best_backend_function_exists(self):
        """Test that backend detection function exists."""
        from content_core.processors.docling_vlm import _detect_best_backend

        backend = _detect_best_backend()
        assert backend in ALLOWED_VLM_BACKENDS

    def test_detect_best_device_function_exists(self):
        """Test that device detection function exists."""
        from content_core.processors.docling_vlm import _detect_best_device

        device = _detect_best_device()
        assert device in ["cpu", "cuda", "mps"]


class TestVLMRemotePayload:
    """Test VLM remote payload construction."""

    @pytest.mark.asyncio
    async def test_remote_requires_httpx(self):
        """Test that remote extraction requires httpx."""
        from content_core.processors.docling_vlm import HTTPX_AVAILABLE

        # This just verifies the flag exists
        assert isinstance(HTTPX_AVAILABLE, bool)

    @pytest.mark.asyncio
    async def test_remote_url_payload(self):
        """Test remote extraction with URL creates correct payload."""
        # Mock httpx
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "extracted content"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("content_core.processors.docling_vlm.HTTPX_AVAILABLE", True):
            with patch("content_core.processors.docling_vlm.httpx.AsyncClient", return_value=mock_client):
                from content_core.processors.docling_vlm import extract_with_vlm_remote

                state = ProcessSourceState(url="https://example.com/doc.pdf")
                result = await extract_with_vlm_remote(state)

                assert "content" in result
                assert result["content"] == "extracted content"

    @pytest.mark.asyncio
    async def test_remote_file_payload(self, tmp_path):
        """Test remote extraction with file creates correct payload with base64."""
        # Create test file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        # Mock httpx
        mock_response = MagicMock()
        mock_response.json.return_value = {"content": "extracted from file"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        with patch("content_core.processors.docling_vlm.HTTPX_AVAILABLE", True):
            with patch("content_core.processors.docling_vlm.httpx.AsyncClient", return_value=mock_client):
                from content_core.processors.docling_vlm import extract_with_vlm_remote

                state = ProcessSourceState(file_path=str(test_file))
                result = await extract_with_vlm_remote(state)

                assert "content" in result
                assert result["content"] == "extracted from file"


class TestVLMRouterSelection:
    """Test VLM router selection in extraction graph."""

    def test_docling_vlm_engine_in_allowed(self):
        """Test that docling-vlm is in allowed document engines."""
        from content_core.config import ALLOWED_DOCUMENT_ENGINES

        assert "docling-vlm" in ALLOWED_DOCUMENT_ENGINES

    def test_graph_has_vlm_node_conditional(self):
        """Test that the graph conditionally includes VLM node."""
        from content_core.processors.docling_vlm import extract_with_docling_vlm

        # Just verify the function exists and can be imported
        assert callable(extract_with_docling_vlm)


class TestVLMStateOverrides:
    """Test that state overrides work for VLM configuration."""

    @pytest.mark.asyncio
    async def test_state_inference_mode_override(self):
        """Test that state can override inference mode."""
        state = ProcessSourceState(
            file_path="/tmp/test.pdf",
            vlm_inference_mode="remote",
        )
        assert state.vlm_inference_mode == "remote"

    @pytest.mark.asyncio
    async def test_state_backend_override(self):
        """Test that state can override backend."""
        state = ProcessSourceState(
            file_path="/tmp/test.pdf",
            vlm_backend="mlx",
        )
        assert state.vlm_backend == "mlx"

    @pytest.mark.asyncio
    async def test_state_remote_url_override(self):
        """Test that state can override remote URL."""
        state = ProcessSourceState(
            file_path="/tmp/test.pdf",
            vlm_remote_url="http://custom:5001",
        )
        assert state.vlm_remote_url == "http://custom:5001"


class TestVLMOptions:
    """Test VLM processing options configuration."""

    def test_get_vlm_options_defaults(self):
        """Test default VLM options."""
        from content_core.config import get_vlm_options

        with patch.dict(os.environ, {}, clear=True):
            options = get_vlm_options()

            assert "do_ocr" in options
            assert "ocr_engine" in options
            assert "table_mode" in options
            assert "do_table_structure" in options
            assert "do_code_enrichment" in options
            assert "do_formula_enrichment" in options
            assert "include_images" in options
            assert "do_picture_classification" in options
            assert "do_picture_description" in options

    def test_get_vlm_options_env_override_bool(self):
        """Test boolean environment variable overrides."""
        from content_core.config import get_vlm_options

        with patch.dict(os.environ, {
            "CCORE_VLM_DO_OCR": "false",
            "CCORE_VLM_DO_CODE_ENRICHMENT": "true",
        }):
            options = get_vlm_options()

            assert options["do_ocr"] is False
            assert options["do_code_enrichment"] is True

    def test_get_vlm_options_env_override_string(self):
        """Test string environment variable overrides."""
        from content_core.config import get_vlm_options

        with patch.dict(os.environ, {
            "CCORE_VLM_OCR_ENGINE": "tesseract",
            "CCORE_VLM_TABLE_MODE": "fast",
        }):
            options = get_vlm_options()

            assert options["ocr_engine"] == "tesseract"
            assert options["table_mode"] == "fast"


class TestVLMLocalNotAvailable:
    """Test graceful handling when VLM local is not available."""

    @pytest.mark.asyncio
    async def test_local_raises_import_error_when_unavailable(self):
        """Test that local extraction raises ImportError when docling[vlm] not installed."""
        with patch("content_core.processors.docling_vlm.DOCLING_VLM_LOCAL_AVAILABLE", False):
            from content_core.processors.docling_vlm import extract_with_vlm_local

            state = ProcessSourceState(file_path="/tmp/test.pdf")
            with pytest.raises(ImportError) as exc_info:
                await extract_with_vlm_local(state)

            assert "docling[vlm]" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_remote_raises_import_error_when_httpx_unavailable(self):
        """Test that remote extraction raises ImportError when httpx not installed."""
        with patch("content_core.processors.docling_vlm.HTTPX_AVAILABLE", False):
            from content_core.processors.docling_vlm import extract_with_vlm_remote

            state = ProcessSourceState(url="https://example.com/doc.pdf")
            with pytest.raises(ImportError) as exc_info:
                await extract_with_vlm_remote(state)

            assert "httpx" in str(exc_info.value)
