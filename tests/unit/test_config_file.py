"""Unit tests for TOML config file support."""
from unittest.mock import patch

import pytest

from content_core.config import (
    ContentCoreConfig,
    config_set,
    config_delete,
    config_list,
    _read_config_file,
    _write_config_file,
)


@pytest.fixture
def config_dir(tmp_path):
    """Use a temp dir instead of ~/.content-core."""
    config_file = tmp_path / "config.toml"
    with (
        patch("content_core.config.CONFIG_DIR", tmp_path),
        patch("content_core.config.CONFIG_FILE", config_file),
    ):
        yield tmp_path, config_file


class TestConfigFile:
    def test_read_empty_when_no_file(self, config_dir):
        assert _read_config_file() == {}

    def test_write_and_read(self, config_dir):
        _write_config_file({"llm_provider": "anthropic", "stt_timeout": 600})
        data = _read_config_file()
        assert data["llm_provider"] == "anthropic"
        assert data["stt_timeout"] == 600

    def test_write_list_value(self, config_dir):
        _write_config_file({"youtube_languages": ["en", "pt"]})
        data = _read_config_file()
        assert data["youtube_languages"] == ["en", "pt"]

    def test_write_bool_value(self, config_dir):
        _write_config_file({"some_bool": True})
        data = _read_config_file()
        assert data["some_bool"] is True


class TestConfigSet:
    def test_set_string_value(self, config_dir):
        config_set("llm_provider", "anthropic")
        assert config_list()["llm_provider"] == "anthropic"

    def test_set_int_value(self, config_dir):
        config_set("stt_timeout", "1800")
        assert config_list()["stt_timeout"] == 1800

    def test_set_list_value(self, config_dir):
        config_set("youtube_languages", "en,pt,fr")
        assert config_list()["youtube_languages"] == ["en", "pt", "fr"]

    def test_set_docling_bool_flags(self, config_dir):
        config_set("docling_formulas", "true")
        config_set("docling_vision", "true")
        config_set("docling_ocr", "false")
        data = config_list()
        # Bool fields are stored as booleans in TOML
        assert data["docling_formulas"] is True
        assert data["docling_vision"] is True
        assert data["docling_ocr"] is False

    def test_set_docling_remote_settings(self, config_dir):
        config_set("docling_api_url", "https://docling.example")
        config_set("docling_api_key", "secret-token")
        config_set("docling_timeout", "120")
        data = config_list()
        assert data["docling_api_url"] == "https://docling.example"
        assert data["docling_api_key"] == "secret-token"
        assert data["docling_timeout"] == 120

    def test_set_invalid_key_raises(self, config_dir):
        with pytest.raises(ValueError, match="Unknown config key"):
            config_set("nonexistent_key", "value")

    def test_set_overwrites_existing(self, config_dir):
        config_set("llm_provider", "openai")
        config_set("llm_provider", "anthropic")
        assert config_list()["llm_provider"] == "anthropic"


class TestConfigDelete:
    def test_delete_existing_key(self, config_dir):
        config_set("llm_provider", "anthropic")
        config_delete("llm_provider")
        assert "llm_provider" not in config_list()

    def test_delete_missing_key_raises(self, config_dir):
        with pytest.raises(KeyError, match="not found"):
            config_delete("llm_provider")


class TestConfigPrecedence:
    def test_toml_overrides_default(self, config_dir):
        _write_config_file({"llm_provider": "anthropic"})
        cfg = ContentCoreConfig()
        assert cfg.llm_provider == "anthropic"

    def test_env_overrides_toml(self, config_dir, monkeypatch):
        _write_config_file({"llm_provider": "anthropic"})
        monkeypatch.setenv("CCORE_LLM_PROVIDER", "google")
        cfg = ContentCoreConfig()
        assert cfg.llm_provider == "google"

    def test_init_overrides_env(self, config_dir, monkeypatch):
        _write_config_file({"llm_provider": "anthropic"})
        monkeypatch.setenv("CCORE_LLM_PROVIDER", "google")
        cfg = ContentCoreConfig(llm_provider="mistral")
        assert cfg.llm_provider == "mistral"

    def test_default_when_no_toml(self, config_dir):
        cfg = ContentCoreConfig()
        assert cfg.llm_provider == "openai"
