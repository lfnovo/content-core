"""Content Core MCP Server — extract and summarize content."""
import sys

from fastmcp import FastMCP
from loguru import logger

# Configure loguru for MCP (stderr only, no stdout interference)
logger.remove()
logger.add(sys.stderr, level="INFO")

mcp = FastMCP("Content Core")


@mcp.tool
async def extract_content(
    url: str = None,
    file_path: str = None,
    engine: str = None,
) -> str:
    """Extract content from a URL or file. Does not require an API key for most sources (web pages, PDFs, documents, YouTube transcripts). API key is only needed for audio/video transcription.

    Args:
        url: URL to extract content from (web page, YouTube video, PDF link, etc.)
        file_path: Local file path to extract content from
        engine: Optional extraction engine override (firecrawl, jina, crawl4ai, simple)

    Returns:
        Extracted text content
    """
    from content_core.config import ContentCoreConfig
    from content_core.extraction import extract_content as _extract
    from content_core.common.state import ExtractionInput

    if not url and not file_path:
        return "Error: Provide either 'url' or 'file_path'"
    if url and file_path:
        return "Error: Provide only one of 'url' or 'file_path', not both"

    config = ContentCoreConfig(url_engine=engine) if engine else None
    inp = ExtractionInput(url=url, file_path=file_path)

    try:
        result = await _extract(inp, config=config)
        return result.content or ""
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return f"Error: {e}"


@mcp.tool
async def summarize_content(
    content: str,
    context: str = "",
) -> str:
    """Summarize content using LLM with optional context. Requires OPENAI_API_KEY (or another LLM provider key) to be configured.

    Args:
        content: The text content to summarize
        context: Optional context to guide summarization (e.g., "summarize as bullet points")

    Returns:
        Summarized text
    """
    from content_core.content.summary import summarize

    try:
        result = await summarize(content, context)
        return result or ""
    except Exception as e:
        error_msg = str(e).lower()
        if "api key" in error_msg or "authentication" in error_msg or "auth" in error_msg or "api_key" in error_msg or "unauthorized" in error_msg:
            logger.error(f"Summarization failed — missing or invalid API key: {e}")
            return (
                "Error: Summarization requires a valid LLM API key (e.g., OPENAI_API_KEY). "
                "The extract_content tool does not require an API key for most sources. "
                "Consider using extract_content instead if you only need the raw content."
            )
        logger.error(f"Summarization failed: {e}")
        return f"Error: {e}"


def main():
    """Entry point for the MCP server."""
    logger.info("Starting Content Core MCP Server")
    mcp.run()


if __name__ == "__main__":
    main()
