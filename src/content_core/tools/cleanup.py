from langchain_core.tools import tool

from content_core.content_cleanup import cleanup_content
from content_core.common import process_input_content


@tool
async def cleanup_content_tool(content: str) -> str:
    """
    Clean content. Rewrite paragraphs. Fix grammar and spelling.
    Accepts direct text, URLs, or file paths. If a URL or file path is provided,
    the content will be extracted first before cleaning.
    """
    content = await process_input_content(content)
    return await cleanup_content(content)
