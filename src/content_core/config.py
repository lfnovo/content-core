"""Content Core configuration (pydantic-settings based)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional, Tuple, Type

from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


CONFIG_DIR = Path.home() / ".content-core"
CONFIG_FILE = CONFIG_DIR / "config.toml"


class TomlFileSettingsSource(PydanticBaseSettingsSource):
    """Read settings from ~/.content-core/config.toml."""

    def get_field_value(
        self, field: Any, field_name: str
    ) -> Tuple[Any, str, bool]:
        data = self._load_toml()
        if field_name in data:
            return data[field_name], field_name, False
        return None, field_name, False

    def _load_toml(self) -> dict:
        if not CONFIG_FILE.exists():
            return {}
        try:
            with open(CONFIG_FILE, "rb") as f:
                return tomllib.load(f)
        except Exception:
            return {}

    def __call__(self) -> dict[str, Any]:
        return self._load_toml()


class ContentCoreConfig(BaseSettings):
    """Content Core configuration.

    Priority: constructor args > environment variables > config file > defaults.
    All env vars are prefixed with CCORE_ (e.g., CCORE_URL_ENGINE=firecrawl).
    Config file: ~/.content-core/config.toml
    """

    model_config = SettingsConfigDict(env_prefix="CCORE_")

    # Engine selection
    document_engine: str = "auto"
    url_engine: str = "auto"

    # Audio
    audio_provider: str = "openai"
    audio_model: Optional[str] = None
    audio_concurrency: int = Field(default=3, ge=1, le=10)

    # Crawl4AI
    crawl4ai_api_url: Optional[str] = None

    # Firecrawl
    firecrawl_api_url: str = "https://api.firecrawl.dev"
    firecrawl_proxy: Optional[str] = "auto"
    firecrawl_wait_for: int = 3000

    # LLM models (for summarize)
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    summary_model: Optional[str] = None  # Falls back to llm_model

    # STT
    stt_provider: str = "openai"
    stt_model: str = "whisper-1"
    stt_timeout: int = 3600

    # YouTube
    youtube_languages: list[str] = Field(default=["en", "es", "pt"])

    # Docling
    docling_output_format: str = "markdown"
    docling_ocr: bool = True
    docling_formulas: bool = False
    docling_vision: bool = False

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            TomlFileSettingsSource(settings_cls),
            file_secret_settings,
        )


_default_config: Optional[ContentCoreConfig] = None


def get_default_config() -> ContentCoreConfig:
    """Get or create the default singleton config."""
    global _default_config
    if _default_config is None:
        _default_config = ContentCoreConfig()
    return _default_config


def reset_default_config() -> None:
    """Reset the singleton config. For testing only."""
    global _default_config
    _default_config = None


# ---------------------------------------------------------------------------
# Config file management (used by CLI `config` subcommands)
# ---------------------------------------------------------------------------

def _read_config_file() -> dict:
    """Read the config file, returning empty dict if missing."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _escape_toml_string(s: str) -> str:
    """Escape backslashes and double quotes for TOML string values."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _write_config_file(data: dict) -> None:
    """Write config data to the TOML file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in sorted(data.items()):
        if isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, int):
            lines.append(f"{key} = {value}")
        elif isinstance(value, list):
            items = ", ".join(f'"{_escape_toml_string(str(v))}"' for v in value)
            lines.append(f"{key} = [{items}]")
        else:
            lines.append(f'{key} = "{_escape_toml_string(str(value))}"')
    CONFIG_FILE.write_text("\n".join(lines) + "\n" if lines else "")


def config_set(key: str, value: str) -> None:
    """Set a config value in the file."""
    # Validate key exists in ContentCoreConfig
    valid_keys = set(ContentCoreConfig.model_fields.keys())
    if key not in valid_keys:
        raise ValueError(f"Unknown config key: {key}. Valid keys: {', '.join(sorted(valid_keys))}")

    data = _read_config_file()

    # Coerce value to the right type
    field = ContentCoreConfig.model_fields[key]
    annotation = field.annotation
    if annotation is int or (hasattr(annotation, "__origin__") and annotation is int):
        data[key] = int(value)
    elif annotation is bool:
        data[key] = value.lower() in ("true", "1", "yes")
    elif hasattr(annotation, "__origin__") and getattr(annotation, "__origin__", None) is list:
        data[key] = [v.strip() for v in value.split(",")]
    else:
        data[key] = value

    _write_config_file(data)


def config_delete(key: str) -> None:
    """Delete a config value from the file."""
    data = _read_config_file()
    if key not in data:
        raise KeyError(f"Key '{key}' not found in config file")
    del data[key]
    _write_config_file(data)


def config_list() -> dict:
    """List all config values from the file."""
    return _read_config_file()


# ---------------------------------------------------------------------------
# Helpers used by sub-modules (e.g. processors/url/firecrawl.py)
# ---------------------------------------------------------------------------

DEFAULT_FIRECRAWL_API_URL = "https://api.firecrawl.dev"


def get_crawl4ai_api_url() -> str | None:
    """Return Crawl4AI API URL for Docker mode.

    Checks CRAWL4AI_API_URL env var first (standard convention),
    then falls back to config file / default (None = local mode).
    """
    env_url = os.environ.get("CRAWL4AI_API_URL")
    if env_url:
        return env_url
    return get_default_config().crawl4ai_api_url


def get_firecrawl_api_url() -> str:
    """Return Firecrawl API URL.

    Checks FIRECRAWL_API_URL env var first (standard Firecrawl convention,
    matching FIRECRAWL_API_KEY), then falls back to config file / default.
    """
    env_url = os.environ.get("FIRECRAWL_API_URL")
    if env_url:
        return env_url
    return get_default_config().firecrawl_api_url
