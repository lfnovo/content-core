"""LangChain tool wrapper for content extraction."""
from typing import Dict

from langchain_core.tools import tool

from content_core.extraction import extract_content
from content_core.common.state import ExtractionInput


@tool
async def extract_content_tool(file_path_or_url: str) -> Dict:
    """Extract title, content and metadata from URLs and files.

    Args:
        file_path_or_url: URL or file path to extract content from.

    Returns:
        Dict: Extracted content and metadata.
    """
    if file_path_or_url.startswith("http"):
        inp = ExtractionInput(url=file_path_or_url)
    else:
        inp = ExtractionInput(file_path=file_path_or_url)
    result = await extract_content(inp)
    return result.model_dump()
