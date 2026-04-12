"""Content Core v2 data models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractionInput(BaseModel):
    """Public input for content extraction.

    At least one of content, file_path, or url should be set.
    Validated by the extraction orchestrator.
    """

    content: Optional[str] = None
    file_path: Optional[str] = None
    url: Optional[str] = None


class ExtractionOutput(BaseModel):
    """Public output from content extraction."""

    content: str = ""
    title: str = ""
    source_type: str = ""  # "url", "file", "text"
    identified_type: str = ""  # MIME type or "youtube", "article"
    metadata: dict = Field(default_factory=dict)


__all__ = [
    "ExtractionInput",
    "ExtractionOutput",
]
