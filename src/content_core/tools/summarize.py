from typing import Optional

from langchain_core.tools import tool

from content_core.content_summary import summarize
from content_core.common import process_input_content


@tool
async def summarize_content_tool(content: str, context: Optional[str] = None) -> str:
    """
    Summarize content according to instructions provided via context.
    Accepts direct text, URLs, or file paths. If a URL or file path is provided,
    the content will be extracted first before summarizing.
    """
    content = await process_input_content(content)
    return await summarize(content, context or "")
