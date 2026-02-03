"""Tests for ENV-only configuration functions."""

import os
from unittest.mock import patch

import pytest

from content_core.config import (
    ALLOWED_DOCUMENT_ENGINES,
    ALLOWED_URL_ENGINES,
    DEFAULT_FIRECRAWL_API_URL,
    get_audio_concurrency,
    get_docling_options,
    get_document_engine,
    get_firecrawl_api_url,
    get_marker_options,
    get_model_config,
    get_pymupdf_options,
    get_retry_config,
    get_url_engine,
    get_vlm_backend,
    get_vlm_inference_mode,
    get_vlm_model,
    get_vlm_remote_timeout,
    get_vlm_remote_url,
    get_youtube_preferred_languages,
    reset_config,
    set_audio_concurrency,
    set_document_engine,
    set_firecrawl_api_url,
    set_url_engine,
    set_vlm_backend,
    set_vlm_inference_mode,
    set_vlm_model,
    set_vlm_remote_timeout,
    set_vlm_remote_url,
)


class TestResetConfig:
    """Test reset_config() function."""

    def teardown_method(self):
        """Clean up after each test."""
        reset_config()

    def test_reset_clears_programmatic_overrides(self):
        """Verify reset_config clears all programmatic overrides."""
        set_document_engine("docling")
        set_url_engine("jina")
        assert get_document_engine() == "docling"
        assert get_url_engine() == "jina"

        reset_config()

        # Should return defaults now
        with patch.dict("os.environ", {}, clear=True):
            assert get_document_engine() == "auto"
            assert get_url_engine() == "auto"


class TestDocumentEngineSelection:
    """Test document engine selection."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_document_engine(self):
        """Test default document engine when no env var is set."""
        with patch.dict("os.environ", {}, clear=True):
            engine = get_document_engine()
            assert engine == "auto"

    def test_valid_document_engine_env_var(self):
        """Test valid document engine environment variable override."""
        for engine in ALLOWED_DOCUMENT_ENGINES:
            with patch.dict("os.environ", {"CCORE_DOCUMENT_ENGINE": engine}):
                assert get_document_engine() == engine

    def test_invalid_document_engine_env_var(self):
        """Test invalid document engine environment variable falls back to default."""
        with patch.dict("os.environ", {"CCORE_DOCUMENT_ENGINE": "invalid_engine"}):
            engine = get_document_engine()
            assert engine == "auto"

    def test_programmatic_override_takes_priority(self):
        """Programmatic override should take priority over ENV."""
        with patch.dict("os.environ", {"CCORE_DOCUMENT_ENGINE": "docling"}):
            set_document_engine("marker")
            assert get_document_engine() == "marker"

    def test_empty_string_document_engine(self):
        """Test empty string for document engine env var."""
        with patch.dict("os.environ", {"CCORE_DOCUMENT_ENGINE": ""}):
            engine = get_document_engine()
            assert engine == "auto"


class TestUrlEngineSelection:
    """Test URL engine selection."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_url_engine(self):
        """Test default URL engine when no env var is set."""
        with patch.dict("os.environ", {}, clear=True):
            engine = get_url_engine()
            assert engine == "auto"

    def test_valid_url_engine_env_var(self):
        """Test valid URL engine environment variable override."""
        for engine in ALLOWED_URL_ENGINES:
            with patch.dict("os.environ", {"CCORE_URL_ENGINE": engine}):
                assert get_url_engine() == engine

    def test_invalid_url_engine_env_var(self):
        """Test invalid URL engine environment variable falls back to default."""
        with patch.dict("os.environ", {"CCORE_URL_ENGINE": "invalid_engine"}):
            engine = get_url_engine()
            assert engine == "auto"

    def test_programmatic_override_takes_priority(self):
        """Programmatic override should take priority over ENV."""
        with patch.dict("os.environ", {"CCORE_URL_ENGINE": "jina"}):
            set_url_engine("firecrawl")
            assert get_url_engine() == "firecrawl"


class TestEngineConstants:
    """Test that engine constants contain expected values."""

    def test_document_engine_constants(self):
        """Test document engine allowed values."""
        expected = {"auto", "simple", "docling", "docling-vlm", "marker"}
        assert ALLOWED_DOCUMENT_ENGINES == expected

    def test_url_engine_constants(self):
        """Test URL engine allowed values."""
        expected = {"auto", "simple", "firecrawl", "jina", "crawl4ai"}
        assert ALLOWED_URL_ENGINES == expected


class TestAudioConcurrency:
    """Test audio concurrency configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_audio_concurrency(self):
        """Test default audio concurrency."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_audio_concurrency() == 3

    def test_env_override(self):
        """Test environment variable override."""
        with patch.dict("os.environ", {"CCORE_AUDIO_CONCURRENCY": "5"}):
            assert get_audio_concurrency() == 5

    def test_invalid_env_fallback(self):
        """Test invalid value falls back to default."""
        with patch.dict("os.environ", {"CCORE_AUDIO_CONCURRENCY": "20"}):
            assert get_audio_concurrency() == 3

    def test_programmatic_override(self):
        """Test programmatic override."""
        set_audio_concurrency(7)
        assert get_audio_concurrency() == 7

    def test_programmatic_validation(self):
        """Test programmatic validation."""
        with pytest.raises(ValueError):
            set_audio_concurrency(0)
        with pytest.raises(ValueError):
            set_audio_concurrency(11)


class TestFirecrawlApiUrl:
    """Test Firecrawl API URL configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_firecrawl_api_url(self):
        """Test default Firecrawl API URL."""
        with patch.dict("os.environ", {}, clear=True):
            url = get_firecrawl_api_url()
            assert url == DEFAULT_FIRECRAWL_API_URL
            assert url == "https://api.firecrawl.dev"

    def test_env_var_override(self):
        """Test environment variable overrides default."""
        custom_url = "http://localhost:3002"
        with patch.dict("os.environ", {"FIRECRAWL_API_BASE_URL": custom_url}):
            url = get_firecrawl_api_url()
            assert url == custom_url

    def test_programmatic_override(self):
        """Test programmatic override via set_firecrawl_api_url."""
        custom_url = "http://programmatic:3002"
        with patch.dict("os.environ", {}, clear=True):
            set_firecrawl_api_url(custom_url)
            url = get_firecrawl_api_url()
            assert url == custom_url

    def test_programmatic_override_beats_env(self):
        """Programmatic override takes precedence over ENV."""
        env_url = "http://env:3002"
        programmatic_url = "http://programmatic:3002"
        with patch.dict("os.environ", {"FIRECRAWL_API_BASE_URL": env_url}):
            set_firecrawl_api_url(programmatic_url)
            url = get_firecrawl_api_url()
            assert url == programmatic_url


class TestVLMConfiguration:
    """Test VLM configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_vlm_inference_mode(self):
        """Test default VLM inference mode."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_vlm_inference_mode() == "local"

    def test_vlm_inference_mode_env(self):
        """Test VLM inference mode from ENV."""
        with patch.dict("os.environ", {"CCORE_VLM_INFERENCE_MODE": "remote"}):
            assert get_vlm_inference_mode() == "remote"

    def test_vlm_inference_mode_programmatic(self):
        """Test programmatic VLM inference mode override."""
        set_vlm_inference_mode("remote")
        assert get_vlm_inference_mode() == "remote"

    def test_vlm_inference_mode_validation(self):
        """Test VLM inference mode validation."""
        with pytest.raises(ValueError):
            set_vlm_inference_mode("invalid")

    def test_default_vlm_backend(self):
        """Test default VLM backend."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_vlm_backend() == "auto"

    def test_vlm_backend_env(self):
        """Test VLM backend from ENV."""
        with patch.dict("os.environ", {"CCORE_VLM_BACKEND": "mlx"}):
            assert get_vlm_backend() == "mlx"

    def test_vlm_backend_programmatic(self):
        """Test programmatic VLM backend override."""
        set_vlm_backend("transformers")
        assert get_vlm_backend() == "transformers"

    def test_default_vlm_model(self):
        """Test default VLM model."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_vlm_model() == "granite-docling"

    def test_vlm_model_env(self):
        """Test VLM model from ENV."""
        with patch.dict("os.environ", {"CCORE_VLM_MODEL": "smol-docling"}):
            assert get_vlm_model() == "smol-docling"

    def test_vlm_model_programmatic(self):
        """Test programmatic VLM model override."""
        set_vlm_model("smol-docling")
        assert get_vlm_model() == "smol-docling"

    def test_default_vlm_remote_url(self):
        """Test default VLM remote URL."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_vlm_remote_url() == "http://localhost:5001"

    def test_vlm_remote_url_env(self):
        """Test VLM remote URL from ENV."""
        with patch.dict(
            "os.environ", {"CCORE_DOCLING_SERVE_URL": "http://custom:8000"}
        ):
            assert get_vlm_remote_url() == "http://custom:8000"

    def test_vlm_remote_url_programmatic(self):
        """Test programmatic VLM remote URL override."""
        set_vlm_remote_url("http://override:9000")
        assert get_vlm_remote_url() == "http://override:9000"

    def test_default_vlm_remote_timeout(self):
        """Test default VLM remote timeout."""
        with patch.dict("os.environ", {}, clear=True):
            assert get_vlm_remote_timeout() == 120

    def test_vlm_remote_timeout_env(self):
        """Test VLM remote timeout from ENV."""
        with patch.dict("os.environ", {"CCORE_DOCLING_SERVE_TIMEOUT": "300"}):
            assert get_vlm_remote_timeout() == 300

    def test_vlm_remote_timeout_programmatic(self):
        """Test programmatic VLM remote timeout override."""
        set_vlm_remote_timeout(180)
        assert get_vlm_remote_timeout() == 180

    def test_vlm_remote_timeout_validation(self):
        """Test VLM remote timeout validation."""
        with pytest.raises(ValueError):
            set_vlm_remote_timeout(0)
        with pytest.raises(ValueError):
            set_vlm_remote_timeout(4000)


class TestDoclingOptions:
    """Test docling options configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_docling_options(self):
        """Test default docling options."""
        with patch.dict("os.environ", {}, clear=True):
            options = get_docling_options()
            assert options["do_ocr"] is True
            assert options["ocr_engine"] == "easyocr"
            assert options["output_format"] == "markdown"
            assert options["do_formula_enrichment"] is True
            assert options["do_picture_description"] is False

    def test_docling_env_overrides(self):
        """Test docling options from ENV."""
        env = {
            "CCORE_DOCLING_DO_OCR": "false",
            "CCORE_DOCLING_OUTPUT_FORMAT": "html",
            "CCORE_DOCLING_DO_PICTURE_DESCRIPTION": "true",
        }
        with patch.dict("os.environ", env):
            options = get_docling_options()
            assert options["do_ocr"] is False
            assert options["output_format"] == "html"
            assert options["do_picture_description"] is True


class TestMarkerOptions:
    """Test Marker options configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_marker_options(self):
        """Test default Marker options."""
        with patch.dict("os.environ", {}, clear=True):
            options = get_marker_options()
            assert options["use_llm"] is False
            assert options["force_ocr"] is False
            assert options["page_range"] is None
            assert options["output_format"] == "markdown"

    def test_marker_env_overrides(self):
        """Test Marker options from ENV."""
        env = {
            "CCORE_MARKER_USE_LLM": "true",
            "CCORE_MARKER_FORCE_OCR": "true",
            "CCORE_MARKER_PAGE_RANGE": "0-10",
        }
        with patch.dict("os.environ", env):
            options = get_marker_options()
            assert options["use_llm"] is True
            assert options["force_ocr"] is True
            assert options["page_range"] == "0-10"


class TestPymupdfOptions:
    """Test PyMuPDF options configuration."""

    def setup_method(self):
        reset_config()

    def teardown_method(self):
        reset_config()

    def test_default_pymupdf_options(self):
        """Test default PyMuPDF options."""
        with patch.dict("os.environ", {}, clear=True):
            options = get_pymupdf_options()
            assert options["enable_formula_ocr"] is False
            assert options["formula_threshold"] == 3
            assert options["ocr_fallback"] is True

    def test_pymupdf_env_overrides(self):
        """Test PyMuPDF options from ENV."""
        env = {
            "CCORE_PYMUPDF_ENABLE_FORMULA_OCR": "true",
            "CCORE_PYMUPDF_FORMULA_THRESHOLD": "5",
        }
        with patch.dict("os.environ", env):
            options = get_pymupdf_options()
            assert options["enable_formula_ocr"] is True
            assert options["formula_threshold"] == 5


class TestRetryConfig:
    """Test retry configuration."""

    def test_default_youtube_retry(self):
        """Test default YouTube retry config."""
        with patch.dict("os.environ", {}, clear=True):
            config = get_retry_config("youtube")
            assert config["max_attempts"] == 5
            assert config["base_delay"] == 2
            assert config["max_delay"] == 60

    def test_env_override_youtube_retry(self):
        """Test ENV override for YouTube retry."""
        with patch.dict("os.environ", {"CCORE_YOUTUBE_MAX_RETRIES": "10"}):
            config = get_retry_config("youtube")
            assert config["max_attempts"] == 10

    def test_unknown_operation_type(self):
        """Test unknown operation type falls back to url_network."""
        config = get_retry_config("unknown")
        assert config["max_attempts"] == 3  # url_network default


class TestYoutubeConfig:
    """Test YouTube configuration."""

    def test_default_languages(self):
        """Test default preferred languages."""
        with patch.dict("os.environ", {}, clear=True):
            langs = get_youtube_preferred_languages()
            assert langs == ["en", "es", "pt"]

    def test_env_override_languages(self):
        """Test ENV override for preferred languages."""
        with patch.dict("os.environ", {"CCORE_YOUTUBE_LANGUAGES": "de,fr,it"}):
            langs = get_youtube_preferred_languages()
            assert langs == ["de", "fr", "it"]


class TestModelConfig:
    """Test model configuration."""

    def test_default_speech_to_text_config(self):
        """Test default speech-to-text config."""
        with patch.dict("os.environ", {}, clear=True):
            config = get_model_config("speech_to_text")
            assert config["provider"] == "openai"
            assert config["model_name"] == "gpt-4o-transcribe-diarize"
            assert config["timeout"] == 3600

    def test_default_llm_config(self):
        """Test default LLM config."""
        with patch.dict("os.environ", {}, clear=True):
            config = get_model_config("default_model")
            assert config["provider"] == "openai"
            assert config["model_name"] == "gpt-4o-mini"
            assert config["config"]["temperature"] == 0.5

    def test_env_override_model_config(self):
        """Test ENV override for model config."""
        env = {
            "CCORE_DEFAULT_MODEL_PROVIDER": "anthropic",
            "CCORE_DEFAULT_MODEL_MODEL": "claude-3-sonnet",
        }
        with patch.dict("os.environ", env):
            config = get_model_config("default_model")
            assert config["provider"] == "anthropic"
            assert config["model_name"] == "claude-3-sonnet"

    def test_unknown_model_alias(self):
        """Test unknown model alias raises ValueError."""
        with pytest.raises(ValueError):
            get_model_config("unknown_model")
