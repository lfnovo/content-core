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


class FileSupport(BaseModel):
    """Verdict from a pre-flight file-support check.

    Returned by ``check_file_support`` so callers can validate an upload
    cheaply (identification + routing only, no extraction) before committing
    to a full extraction job.
    """

    supported: bool
    file_path: str
    identified_type: str = ""  # MIME type detected for the file
    document_engine: str = ""  # engine the verdict was computed for
    processor: Optional[str] = None  # processor that would handle it, if supported
    reason: Optional[str] = None  # human-readable explanation when unsupported


__all__ = [
    "ExtractionInput",
    "ExtractionOutput",
    "FileSupport",
]
