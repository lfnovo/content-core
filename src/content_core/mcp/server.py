"""Content Core MCP Server implementation."""

import os
import sys
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Optional

from fastmcp import FastMCP
from loguru import logger

# Suppress MoviePy output for MCP compatibility
os.environ["IMAGEIO_LOG_LEVEL"] = "error"
os.environ["FFMPEG_LOG_LEVEL"] = "error"

# Configure loguru to not output to stdout (which would interfere with MCP)
logger.remove()  # Remove default handler
logger.add(sys.stderr, level="INFO")  # Add stderr handler only


@contextmanager
def suppress_stdout():
    """Context manager to suppress stdout during operations that might print."""
    original_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        yield
    finally:
        sys.stdout = original_stdout


# Add parent directory to path to import content_core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import content_core as cc

# Initialize MCP server
mcp = FastMCP("Content Core MCP Server")


async def _extract_content_impl(
    url: Optional[str] = None, file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract content from a URL or file using Content Core's auto engine. This is useful for processing Youtube transcripts, website content, PDFs, ePUB, Office files, etc. You can also use it to extract transcripts from audio or video files.

    Args:
        url: Optional URL to extract content from
        file_path: Optional file path to extract content from

    Returns:
        JSON object containing extracted content and metadata

    Raises:
        ValueError: If neither or both url and file_path are provided
    """
    # Validate input - exactly one must be provided
    if (url is None and file_path is None) or (
        url is not None and file_path is not None
    ):
        return {
            "success": False,
            "error": "Exactly one of 'url' or 'file_path' must be provided",
            "source_type": None,
            "source": None,
            "content": None,
            "metadata": None,
        }

    # Determine source type and validate
    source_type = "url" if url else "file"
    source = url if url else file_path

    # Additional validation for file paths
    if file_path:
        path = Path(file_path)
        if not path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "source_type": source_type,
                "source": source,
                "content": None,
                "metadata": None,
            }

        # Security check - ensure no directory traversal
        try:
            # Resolve to absolute path and ensure it's not trying to access sensitive areas
            path.resolve()
            # You might want to add additional checks here based on your security requirements
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid file path: {str(e)}",
                "source_type": source_type,
                "source": source,
                "content": None,
                "metadata": None,
            }

    # Build extraction request
    extraction_request = {}
    if url:
        extraction_request["url"] = url
    else:
        extraction_request["file_path"] = str(Path(file_path).resolve())

    # Track start time
    start_time = datetime.utcnow()

    try:
        # Use Content Core's extract_content with auto engine
        logger.info(f"Extracting content from {source_type}: {source}")

        # Suppress stdout to prevent MoviePy and other libraries from interfering with MCP protocol
        with suppress_stdout():
            result = await cc.extract_content(extraction_request)

        # Calculate extraction time
        extraction_time = (datetime.utcnow() - start_time).total_seconds()

        # Build response - result is a ProcessSourceOutput object
        response = {
            "success": True,
            "error": None,
            "source_type": source_type,
            "source": source,
            "content": result.content or "",
            "metadata": {
                "extraction_time_seconds": extraction_time,
                "extraction_timestamp": start_time.isoformat() + "Z",
                "content_length": len(result.content or ""),
                "identified_type": result.identified_type or "unknown",
                "identified_provider": result.identified_provider or "",
            },
        }

        # Add metadata from the result
        if result.metadata:
            response["metadata"].update(result.metadata)

        # Add specific metadata based on source type
        if source_type == "url":
            if result.title:
                response["metadata"]["title"] = result.title
            if result.url:
                response["metadata"]["final_url"] = result.url
        elif source_type == "file":
            if result.title:
                response["metadata"]["title"] = result.title
            if result.file_path:
                response["metadata"]["file_path"] = result.file_path
            response["metadata"]["file_size"] = Path(file_path).stat().st_size
            response["metadata"]["file_extension"] = Path(file_path).suffix

        logger.info(f"Successfully extracted content from {source_type}: {source}")
        return response

    except Exception as e:
        logger.error(f"Error extracting content from {source_type} {source}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "source_type": source_type,
            "source": source,
            "content": None,
            "metadata": {
                "extraction_timestamp": start_time.isoformat() + "Z",
                "error_type": type(e).__name__,
            },
        }


@mcp.tool
async def extract_content(
    url: Optional[str] = None, file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract content from a URL or file using Content Core's auto engine.

    Args:
        url: Optional URL to extract content from
        file_path: Optional file path to extract content from

    Returns:
        JSON object containing extracted content and metadata

    Raises:
        ValueError: If neither or both url and file_path are provided
    """
    return await _extract_content_impl(url=url, file_path=file_path)


def main():
    """Entry point for the MCP server."""
    # Additional MoviePy configuration to suppress all output
    try:
        import moviepy.config as mp_config

        mp_config.check_and_download_cmd("ffmpeg")  # Pre-download to avoid logs later
    except Exception:
        pass  # Ignore if MoviePy isn't available or configured

    logger.info("Starting Content Core MCP Server")

    # Run with STDIO transport for MCP compatibility
    mcp.run()


if __name__ == "__main__":
    main()
