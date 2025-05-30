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
        description="Override URL extraction engine: 'auto', 'simple', 'firecrawl', 'jina', or 'docling'",
    )
    output_format: Optional[str] = Field(
        default=None,
        description="Override Docling output format: 'markdown', 'html', or 'json'",
    )


class ProcessSourceInput(BaseModel):
    content: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    document_engine: Optional[str] = None
    url_engine: Optional[str] = None
    output_format: Optional[str] = None


class ProcessSourceOutput(BaseModel):
    title: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    source_type: Optional[str] = ""
    identified_type: Optional[str] = ""
    identified_provider: Optional[str] = ""
    metadata: Optional[dict] = Field(default_factory=lambda: {})
    content: Optional[str] = ""
