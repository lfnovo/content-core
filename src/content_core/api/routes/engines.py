"""Engine listing endpoints."""

import os
from typing import Optional, Type

from fastapi import APIRouter, Query

from content_core.api.schemas import EngineInfo, EnginesResponse
from content_core.processors import ProcessorRegistry
from content_core.processors.base import Processor

router = APIRouter(tags=["engines"])


def _get_unavailability_reason(processor_cls: Type[Processor]) -> Optional[str]:
    """Determine why a processor is unavailable.

    Args:
        processor_cls: The processor class to check.

    Returns:
        Human-readable reason string, or None if available.
    """
    if processor_cls.is_available():
        return None

    name = processor_cls.name
    caps = processor_cls.capabilities
    requires = caps.requires

    # Special case for firecrawl - needs API key
    if name == "firecrawl":
        if not os.environ.get("FIRECRAWL_API_KEY"):
            return "Requires FIRECRAWL_API_KEY environment variable"

    # Check if it's a dependency issue
    if requires:
        return f"Missing dependency. Install with: pip install content-core[{requires[0]}]"

    return "Not available (unknown reason)"


@router.get("/engines", response_model=EnginesResponse)
async def list_engines(
    include_unavailable: bool = Query(
        default=False,
        description="Include unavailable engines in the response",
    ),
) -> EnginesResponse:
    """List extraction engines.

    By default, only returns available (registered) engines. Set
    `include_unavailable=true` to include all engines with reasons
    for why they're unavailable.

    Returns information about each engine including supported MIME types,
    file extensions, and availability status.
    """
    registry = ProcessorRegistry.instance()
    engines: list[EngineInfo] = []

    if include_unavailable:
        # Return all decorated processors (available and unavailable)
        for processor_cls in ProcessorRegistry._all_processors:
            caps = processor_cls.capabilities
            available = processor_cls.is_available()
            reason = _get_unavailability_reason(processor_cls) if not available else None

            engines.append(
                EngineInfo(
                    name=processor_cls.name,
                    available=available,
                    reason=reason,
                    mime_types=caps.mime_types,
                    extensions=caps.extensions,
                    priority=caps.priority,
                    category=caps.category,
                    requires=caps.requires,
                )
            )
    else:
        # Return only available (registered) processors
        for processor_cls in registry.list_available():
            caps = processor_cls.capabilities
            engines.append(
                EngineInfo(
                    name=processor_cls.name,
                    available=True,
                    reason=None,
                    mime_types=caps.mime_types,
                    extensions=caps.extensions,
                    priority=caps.priority,
                    category=caps.category,
                    requires=caps.requires,
                )
            )

    # Sort by priority (highest first)
    engines.sort(key=lambda e: e.priority, reverse=True)

    return EnginesResponse(engines=engines)
