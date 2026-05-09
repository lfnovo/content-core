"""LangChain tool wrapper for content extraction."""
from typing import Dict

from langchain_core.tools import tool

from content_core.extraction import extract_content


@tool
async def extract_content_tool(file_path_or_url: str) -> Dict:
    """Extract title, content and metadata from URLs and files.

    Args:
        file_path_or_url: URL or file path to extract content from.

    Returns:
        Dict: Extracted content and metadata.
    """
    if file_path_or_url.startswith("http"):
        result = await extract_content(url=file_path_or_url)
    else:
        result = await extract_content(file_path=file_path_or_url)
    return result.model_dump()
