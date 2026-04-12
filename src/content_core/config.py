"""Content Core configuration (pydantic-settings based)."""
from __future__ import annotations

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContentCoreConfig(BaseSettings):
    """Content Core configuration.

    Priority: constructor args > environment variables > defaults.
    All env vars are prefixed with CCORE_ (e.g., CCORE_URL_ENGINE=firecrawl).
    """

    model_config = SettingsConfigDict(env_prefix="CCORE_")

    # Engine selection
    document_engine: str = "auto"
    url_engine: str = "auto"

    # Audio
    audio_provider: str = "openai"
    audio_model: Optional[str] = None
    audio_concurrency: int = Field(default=3, ge=1, le=10)

    # Firecrawl
    firecrawl_api_url: str = "https://api.firecrawl.dev"

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

    # PyMuPDF OCR
    pymupdf_enable_formula_ocr: bool = False
    pymupdf_formula_threshold: int = 3
    pymupdf_ocr_fallback: bool = True

    # Docling
    docling_output_format: str = "markdown"


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
# Helpers used by sub-modules (e.g. processors/url/firecrawl.py)
# ---------------------------------------------------------------------------

DEFAULT_FIRECRAWL_API_URL = "https://api.firecrawl.dev"


def get_firecrawl_api_url() -> str:
    """Return firecrawl_api_url from default config."""
    return get_default_config().firecrawl_api_url
