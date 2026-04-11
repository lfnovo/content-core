"""Content extraction — redirects to new extraction module."""
from typing import Dict, Union

from content_core.extraction import extract_content as _extract_content_v2
from content_core.models_v2 import ExtractionInput, ExtractionOutput

# Backward compatibility aliases
ProcessSourceInput = ExtractionInput
ProcessSourceOutput = ExtractionOutput


async def extract_content(data) -> ExtractionOutput:
    """Backward-compatible wrapper around the new extraction module.

    Accepts ExtractionInput, old ProcessSourceInput, or a dict.
    """
    if isinstance(data, dict):
        return await _extract_content_v2(data)
    if hasattr(data, "model_dump"):
        d = data.model_dump()
        return await _extract_content_v2(d)
    return await _extract_content_v2(data)


__all__ = ["extract_content", "ExtractionInput", "ExtractionOutput"]
