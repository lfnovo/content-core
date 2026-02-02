"""Content extraction module.

This module provides the main `extract_content()` function for extracting
content from URLs, files, and raw text.

Two API styles are supported:

1. New API (v2.0) - Named parameters:
    ```python
    result = await extract_content(url="https://example.com/doc.pdf")
    result = await extract_content(file_path="/path/to/file.pdf", engine="docling")
    result = await extract_content(content="Hello world", mime_type="text/plain")
    ```

2. Legacy API - Dict or ProcessSourceInput:
    ```python
    result = await extract_content({"url": "https://example.com/doc.pdf"})
    result = await extract_content(ProcessSourceInput(file_path="/path/to/file.pdf"))
    ```

The new API returns ExtractionResult, while the legacy API returns ProcessSourceOutput.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union, overload

from pydantic import BaseModel

from content_core.common import (
    ExtractionResult,
    ProcessSourceInput,
    ProcessSourceOutput,
)
from content_core.content.extraction.graph import graph


@overload
async def extract_content(
    data: Union[ProcessSourceInput, Dict],
) -> ProcessSourceOutput: ...


@overload
async def extract_content(
    *,
    url: str,
    engine: Optional[Union[str, List[str]]] = None,
    timeout: int = 300,
    options: Optional[Union[Dict[str, Any], BaseModel]] = None,
) -> ExtractionResult: ...


@overload
async def extract_content(
    *,
    file_path: Union[str, Path],
    engine: Optional[Union[str, List[str]]] = None,
    timeout: int = 300,
    options: Optional[Union[Dict[str, Any], BaseModel]] = None,
) -> ExtractionResult: ...


@overload
async def extract_content(
    *,
    content: Union[str, bytes],
    mime_type: Optional[str] = None,
    engine: Optional[Union[str, List[str]]] = None,
    timeout: int = 300,
    options: Optional[Union[Dict[str, Any], BaseModel]] = None,
) -> ExtractionResult: ...


async def extract_content(
    # Legacy API parameter
    data: Optional[Union[ProcessSourceInput, Dict]] = None,
    # New API parameters
    url: Optional[str] = None,
    file_path: Optional[Union[str, Path]] = None,
    content: Optional[Union[str, bytes]] = None,
    mime_type: Optional[str] = None,
    engine: Optional[Union[str, List[str]]] = None,
    timeout: int = 300,
    options: Optional[Union[Dict[str, Any], BaseModel]] = None,
) -> Union[ExtractionResult, ProcessSourceOutput]:
    """Extract content from URL, file, or raw content.

    Supports both new named parameters API and legacy dict/ProcessSourceInput API.

    New API (v2.0):
        result = await extract_content(url="https://example.com/doc.pdf")
        result = await extract_content(file_path="/path/to/file.pdf", engine="docling")
        result = await extract_content(content="raw text", mime_type="text/plain")

    Legacy API:
        result = await extract_content({"url": "https://example.com/doc.pdf"})
        result = await extract_content(ProcessSourceInput(file_path="/path/to/file.pdf"))

    Args:
        data: Legacy API - Dict or ProcessSourceInput with extraction parameters.
        url: URL to extract content from.
        file_path: Path to local file to extract content from.
        content: Raw content (string or bytes) to process.
        mime_type: MIME type of the content (auto-detected if not provided).
        engine: Engine name(s) to use. If a list, tries each in order until success.
            Examples: "docling", "pymupdf4llm", ["docling", "pymupdf4llm"]
        timeout: Timeout in seconds (default: 300).
        options: Additional processor-specific options.

    Returns:
        ExtractionResult (new API) or ProcessSourceOutput (legacy API).

    Raises:
        ValueError: If no source is provided or validation fails.
        ImportError: If the required processor dependencies are not installed.

    Examples:
        # Extract from URL
        result = await extract_content(url="https://example.com/doc.pdf")
        print(result.content)

        # Extract from file with specific engine
        result = await extract_content(
            file_path="/path/to/doc.pdf",
            engine="docling"
        )

        # Extract with fallback chain
        result = await extract_content(
            file_path="/path/to/doc.pdf",
            engine=["docling", "pymupdf4llm", "pymupdf"]
        )

        # Legacy API (still supported)
        result = await extract_content({"url": "https://example.com"})
    """
    # Check if using legacy API
    if data is not None:
        return await _extract_legacy(data)

    # New API - validate exactly one source
    sources = [url, file_path, content]
    provided = [s for s in sources if s is not None]
    if len(provided) == 0:
        raise ValueError("Must provide one of: url, file_path, content")
    if len(provided) > 1:
        raise ValueError("Must provide only one of: url, file_path, content")

    # Convert options if needed
    opts: Optional[Dict[str, Any]] = None
    if options is not None:
        if isinstance(options, BaseModel):
            opts = options.model_dump()
        else:
            opts = options

    # Use new router-based extraction
    from content_core.content.extraction.router import route_and_extract

    result = await route_and_extract(
        file_path=file_path,
        url=url,
        content=content,
        mime_type=mime_type,
        engine=engine,
        options=opts,
    )

    # Convert ProcessorResult to ExtractionResult
    return ExtractionResult(
        content=result.content,
        source_type="file" if file_path else ("url" if url else "content"),
        mime_type=result.mime_type,
        metadata=result.metadata,
        engine_used=result.metadata.get("extraction_engine", ""),
        warnings=result.warnings,
    )


async def _extract_legacy(
    data: Union[ProcessSourceInput, Dict],
) -> ProcessSourceOutput:
    """Extract content using the legacy LangGraph-based workflow.

    This maintains backward compatibility with existing code.

    Args:
        data: Dict or ProcessSourceInput with extraction parameters.

    Returns:
        ProcessSourceOutput with extracted content.
    """
    if isinstance(data, dict):
        data = ProcessSourceInput(**data)
    result = await graph.ainvoke(data)
    return ProcessSourceOutput(**result)


# Export for convenience
__all__ = ["extract_content", "ExtractionResult"]
