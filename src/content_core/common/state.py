from typing import Optional

from pydantic import BaseModel, Field


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
    engine: Optional[str] = Field(default=None, description="Override extraction engine: 'legacy' or 'docling'")
    output_format: Optional[str] = Field(default=None, description="Override Docling output format: 'markdown', 'html', or 'json'")


class ProcessSourceInput(BaseModel):
    content: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    engine: Optional[str] = None
    output_format: Optional[str] = None


class ProcessSourceOutput(BaseModel):
    title: Optional[str] = ""
    source_type: Optional[str] = ""
    identified_type: Optional[str] = ""
    identified_provider: Optional[str] = ""
    metadata: Optional[dict] = Field(default_factory=lambda: {})
    content: Optional[str] = ""
