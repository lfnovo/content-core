"""LangChain tool wrapper for content summarization."""
from langchain_core.tools import tool

from content_core.content.summary import summarize


@tool
async def summarize_content_tool(content: str, context: str = "") -> str:
    """Summarize content with optional context.

    Args:
        content: The content to summarize.
        context: Optional context for the summarization.

    Returns:
        str: Summarized content.
    """
    return await summarize(content, context)
