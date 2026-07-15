"""Tests for ContentCoreConfig (pydantic-settings based config v2)."""
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from content_core.config import (
    ContentCoreConfig,
    get_default_config,
    reset_default_config,
)


@pytest.fixture(autouse=True)
def _isolate_config_file(tmp_path):
    """Point CONFIG_FILE to a non-existent temp path so the developer's
    real ~/.content-core/config.toml never influences test results."""
    fake_config_file = tmp_path / "config.toml"
    with (
        patch("content_core.config.CONFIG_DIR", tmp_path),
        patch("content_core.config.CONFIG_FILE", fake_config_file),
    ):
        yield


@pytest.fixture(autouse=True)
def _clean_singleton():
    """Ensure singleton is reset before and after each test."""
    reset_default_config()
    yield
    reset_default_config()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Remove any CCORE_ env vars that might leak between tests."""
    for key in list(os.environ):
        if key.startswith("CCORE_"):
            monkeypatch.delenv(key, raising=False)
    for key in ("DOCLING_API_URL", "DOCLING_API_KEY"):
        monkeypatch.delenv(key, raising=False)


class TestDefaults:
    """Verify all default values are set correctly."""

    def test_document_engine_default(self):
        cfg = ContentCoreConfig()
        assert cfg.document_engine == "auto"

    def test_url_engine_default(self):
        cfg = ContentCoreConfig()
        assert cfg.url_engine == "auto"

    def test_audio_provider_default(self):
        cfg = ContentCoreConfig()
        assert cfg.audio_provider == "openai"

    def test_audio_model_default(self):
        cfg = ContentCoreConfig()
        assert cfg.audio_model is None

    def test_audio_concurrency_default(self):
        cfg = ContentCoreConfig()
        assert cfg.audio_concurrency == 3

    def test_firecrawl_api_url_default(self):
        cfg = ContentCoreConfig()
        assert cfg.firecrawl_api_url == "https://api.firecrawl.dev"

    def test_llm_provider_default(self):
        cfg = ContentCoreConfig()
        assert cfg.llm_provider == "openai"

    def test_llm_model_default(self):
        cfg = ContentCoreConfig()
        assert cfg.llm_model == "gpt-4o-mini"

    def test_summary_model_default(self):
        cfg = ContentCoreConfig()
        assert cfg.summary_model is None

    def test_stt_provider_default(self):
        cfg = ContentCoreConfig()
        assert cfg.stt_provider == "openai"

    def test_stt_model_default(self):
        cfg = ContentCoreConfig()
        assert cfg.stt_model == "whisper-1"

    def test_stt_timeout_default(self):
        cfg = ContentCoreConfig()
        assert cfg.stt_timeout == 3600

    def test_youtube_languages_default(self):
        cfg = ContentCoreConfig()
        assert cfg.youtube_languages == ["en", "es", "pt"]

    def test_docling_output_format_default(self):
        cfg = ContentCoreConfig()
        assert cfg.docling_output_format == "markdown"

    def test_docling_api_url_default(self):
        cfg = ContentCoreConfig()
        assert cfg.docling_api_url is None

    def test_docling_api_key_default(self):
        cfg = ContentCoreConfig()
        assert cfg.docling_api_key is None

    def test_docling_timeout_default(self):
        cfg = ContentCoreConfig()
        assert cfg.docling_timeout == 300


class TestConstructorOverride:
    """Verify constructor arguments override defaults."""

    def test_url_engine_override(self):
        cfg = ContentCoreConfig(url_engine="firecrawl")
        assert cfg.url_engine == "firecrawl"

    def test_audio_concurrency_override(self):
        cfg = ContentCoreConfig(audio_concurrency=5)
        assert cfg.audio_concurrency == 5

    def test_llm_model_override(self):
        cfg = ContentCoreConfig(llm_model="gpt-4o")
        assert cfg.llm_model == "gpt-4o"


class TestEnvVarOverride:
    """Verify environment variables override defaults."""

    def test_url_engine_from_env(self, monkeypatch):
        monkeypatch.setenv("CCORE_URL_ENGINE", "jina")
        cfg = ContentCoreConfig()
        assert cfg.url_engine == "jina"

    def test_audio_concurrency_from_env(self, monkeypatch):
        monkeypatch.setenv("CCORE_AUDIO_CONCURRENCY", "7")
        cfg = ContentCoreConfig()
        assert cfg.audio_concurrency == 7

    def test_llm_model_from_env(self, monkeypatch):
        monkeypatch.setenv("CCORE_LLM_MODEL", "claude-sonnet")
        cfg = ContentCoreConfig()
        assert cfg.llm_model == "claude-sonnet"

    def test_docling_api_url_from_standard_env(self, monkeypatch):
        monkeypatch.setenv("DOCLING_API_URL", "https://docling.example")
        cfg = ContentCoreConfig()
        assert cfg.docling_api_url == "https://docling.example"

    def test_docling_api_url_from_prefixed_env(self, monkeypatch):
        monkeypatch.setenv("CCORE_DOCLING_API_URL", "https://docling.example")
        cfg = ContentCoreConfig()
        assert cfg.docling_api_url == "https://docling.example"

    def test_docling_api_key_from_standard_env(self, monkeypatch):
        monkeypatch.setenv("DOCLING_API_KEY", "secret-token")
        cfg = ContentCoreConfig()
        assert cfg.docling_api_key == "secret-token"

    def test_docling_timeout_from_prefixed_env(self, monkeypatch):
        monkeypatch.setenv("CCORE_DOCLING_TIMEOUT", "120")
        cfg = ContentCoreConfig()
        assert cfg.docling_timeout == 120


class TestEnvVarListField:
    """Verify list fields can be set via environment variables."""

    def test_youtube_languages_from_env_json(self, monkeypatch):
        monkeypatch.setenv("CCORE_YOUTUBE_LANGUAGES", '["fr", "de"]')
        cfg = ContentCoreConfig()
        assert cfg.youtube_languages == ["fr", "de"]


class TestValidation:
    """Verify field validation constraints."""

    def test_audio_concurrency_too_low(self):
        with pytest.raises(ValidationError):
            ContentCoreConfig(audio_concurrency=0)

    def test_audio_concurrency_too_high(self):
        with pytest.raises(ValidationError):
            ContentCoreConfig(audio_concurrency=11)

    def test_audio_concurrency_min_boundary(self):
        cfg = ContentCoreConfig(audio_concurrency=1)
        assert cfg.audio_concurrency == 1

    def test_audio_concurrency_max_boundary(self):
        cfg = ContentCoreConfig(audio_concurrency=10)
        assert cfg.audio_concurrency == 10


class TestPriority:
    """Verify constructor args beat env vars."""

    def test_constructor_beats_env_var(self, monkeypatch):
        monkeypatch.setenv("CCORE_URL_ENGINE", "jina")
        cfg = ContentCoreConfig(url_engine="firecrawl")
        assert cfg.url_engine == "firecrawl"

    def test_constructor_beats_env_var_llm_model(self, monkeypatch):
        monkeypatch.setenv("CCORE_LLM_MODEL", "from-env")
        cfg = ContentCoreConfig(llm_model="from-constructor")
        assert cfg.llm_model == "from-constructor"

    def test_constructor_beats_docling_standard_env(self, monkeypatch):
        monkeypatch.setenv("DOCLING_API_URL", "https://from-env.example")
        cfg = ContentCoreConfig(docling_api_url="https://from-constructor.example")
        assert cfg.docling_api_url == "https://from-constructor.example"


class TestSingleton:
    """Verify get_default_config / reset_default_config behavior."""

    def test_get_default_config_returns_singleton(self):
        cfg1 = get_default_config()
        cfg2 = get_default_config()
        assert cfg1 is cfg2

    def test_reset_clears_singleton(self):
        cfg1 = get_default_config()
        reset_default_config()
        cfg2 = get_default_config()
        assert cfg1 is not cfg2

    def test_singleton_picks_up_env(self, monkeypatch):
        monkeypatch.setenv("CCORE_URL_ENGINE", "bs4")
        cfg = get_default_config()
        assert cfg.url_engine == "bs4"
