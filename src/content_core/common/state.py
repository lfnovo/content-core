from typing import Optional

from pydantic import BaseModel, Field

from content_core.common.types import DocumentEngine, UrlEngine


class ProcessSourceState(BaseModel):
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    delete_source: bool = False
    title: Optional[str] = ""
    source_type: Optional[str] = ""
    identified_type: Optional[str] = ""
    identified_provider: Optional[str] = ""
    metadata: Optional[dict] = Field(default_factory=lambda: {})
    content: Optional[str] = ""
    document_engine: Optional[DocumentEngine] = Field(
        default=None,
        description="Override document extraction engine: 'auto', 'simple', or 'docling'",
    )
    url_engine: Optional[UrlEngine] = Field(
        default=None,
        description="Override URL extraction engine: 'auto', 'simple', 'firecrawl', 'jina', 'crawl4ai', or 'docling'",
    )
    output_format: Optional[str] = Field(
        default=None,
        description="Override Docling output format: 'markdown', 'html', or 'json'",
    )
    audio_provider: Optional[str] = Field(
        default=None,
        description="Override speech-to-text provider (e.g., 'openai', 'google')",
    )
    audio_model: Optional[str] = Field(
        default=None,
        description="Override speech-to-text model name (e.g., 'whisper-1', 'chirp')",
    )
    vision_provider: Optional[str] = Field(
        default=None,
        description="Vision model provider (e.g., 'openai', 'anthropic')",
    )
    vision_model: Optional[str] = Field(
        default=None,
        description="Vision model name (e.g., 'gpt-4o', 'claude-sonnet-4-5-20250929')",
    )
    audio_config: Optional[dict] = Field(
        default=None,
        description="Config for audio model (api_key, base_url, etc.)",
    )
    vision_config: Optional[dict] = Field(
        default=None,
        description="Config for vision model (api_key, base_url, etc.)",
    )


class ProcessSourceInput(BaseModel):
    content: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    document_engine: Optional[str] = None
    url_engine: Optional[str] = None
    output_format: Optional[str] = None
    audio_provider: Optional[str] = None
    audio_model: Optional[str] = None
    vision_provider: Optional[str] = None
    vision_model: Optional[str] = None
    audio_config: Optional[dict] = None
    vision_config: Optional[dict] = None


class ProcessSourceOutput(BaseModel):
    title: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    source_type: Optional[str] = ""
    identified_type: Optional[str] = ""
    identified_provider: Optional[str] = ""
    metadata: Optional[dict] = Field(default_factory=lambda: {})
    content: Optional[str] = ""
