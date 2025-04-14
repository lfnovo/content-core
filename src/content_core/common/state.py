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


class ProcessSourceInput(BaseModel):
    content: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""


class ProcessSourceOutput(BaseModel):
    title: Optional[str] = ""
    source_type: Optional[str] = ""
    identified_type: Optional[str] = ""
    identified_provider: Optional[str] = ""
    metadata: Optional[dict] = Field(default_factory=lambda: {})
    content: Optional[str] = ""
