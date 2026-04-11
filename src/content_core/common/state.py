from typing import Optional

from pydantic import BaseModel, Field

from content_core.common.types import DocumentEngine, UrlEngine
from content_core.models_v2 import ExtractionInput, ExtractionOutput


# Backward compat — old processors still reference this during transition
# TODO: Remove when old processor functions are deleted
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
    document_engine: Optional[DocumentEngine] = Field(default=None)
    url_engine: Optional[UrlEngine] = Field(default=None)
    output_format: Optional[str] = Field(default=None)
    audio_provider: Optional[str] = Field(default=None)
    audio_model: Optional[str] = Field(default=None)


class ProcessSourceInput(BaseModel):
    content: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    document_engine: Optional[str] = None
    url_engine: Optional[str] = None
    output_format: Optional[str] = None
    audio_provider: Optional[str] = None
    audio_model: Optional[str] = None


class ProcessSourceOutput(BaseModel):
    title: Optional[str] = ""
    file_path: Optional[str] = ""
    url: Optional[str] = ""
    source_type: Optional[str] = ""
    identified_type: Optional[str] = ""
    identified_provider: Optional[str] = ""
    metadata: Optional[dict] = Field(default_factory=lambda: {})
    content: Optional[str] = ""


# Re-export v2 models
__all__ = [
    "ProcessSourceState",
    "ProcessSourceInput",
    "ProcessSourceOutput",
    "ExtractionInput",
    "ExtractionOutput",
]
