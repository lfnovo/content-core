"""Processor Protocol — contract for all content processors."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from content_core.config import ContentCoreConfig
from content_core.common.state import ExtractionOutput


@runtime_checkable
class Processor(Protocol):
    """Contract for content processors.

    Processors receive a source string (file path, URL, or text content)
    and a config object. They return an ExtractionOutput.
    """

    async def extract(self, source: str, config: ContentCoreConfig) -> ExtractionOutput: ...
