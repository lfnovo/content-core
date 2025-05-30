import argparse
import asyncio
import json
import os
import sys
from xml.etree import ElementTree as ET

from dotenv import load_dotenv

load_dotenv()

from dicttoxml import dicttoxml  # type: ignore

from content_core.common import ProcessSourceInput
from content_core.content.cleanup import cleanup_content
from content_core.content.extraction import extract_content
from content_core.content.summary import summarize
from content_core.logging import configure_logging, logger

# Exposing functions for direct access when importing content_core as cc
extract = extract_content
clean = cleanup_content


# Configure loguru logger using centralized configuration
configure_logging(debug=False)


def parse_content_format(content: str) -> str:
    """Parse content that might be JSON or XML, extracting the 'content' field if present."""
    try:
        # Try JSON first
        try:
            json_data = json.loads(content)
            if isinstance(json_data, dict) and "content" in json_data:
                extracted = json_data["content"]
                return str(extracted) if extracted is not None else content
        except json.JSONDecodeError:
            # Try XML
            try:
                root = ET.fromstring(content)
                content_elem = root.find(".//content")
                if content_elem is not None and content_elem.text is not None:
                    return content_elem.text
            except ET.ParseError:
                pass
        return content
    except Exception as e:
        logger.error(f"Error parsing content: {e}")
        return content


def get_content(args, parser, allow_empty=False):
    """Helper to get content from args or stdin."""
    if args.content is None:
        if sys.stdin.isatty():
            parser.error("No content provided. Provide content or pipe input.")
        else:
            content = sys.stdin.read().strip()
    else:
        content = args.content

    if not content and not allow_empty:
        parser.error("Empty input provided.")
    return content


async def process_input_content(content: str) -> str:
    """Process input content, handling URLs and file paths."""
    if "http" in content:
        result = await extract_content(ProcessSourceInput(url=content))
        content = result.content if result.content else str(result)
    elif os.path.exists(content):
        result = await extract_content(ProcessSourceInput(file_path=content))
        content = result.content if result.content else str(result)
    return content


async def ccore_main():
    """CLI logic for ccore (extract)."""
    parser = argparse.ArgumentParser(
        description="Content Core CLI: Extract content with formatting options."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["xml", "json", "text"],
        default="text",
        help="Output format (xml, json, or text). Default: text",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging."
    )
    parser.add_argument(
        "content",
        nargs="?",
        help="Content to process (URL, file path, or text). If not provided, reads from stdin.",
    )

    args = parser.parse_args()

    # Adjust logging level based on debug flag using centralized configuration
    configure_logging(debug=args.debug)
    if args.debug:
        logger.debug("Debug logging enabled")

    content = get_content(args, parser)

    content = await process_input_content(content)

    try:
        result = await extract_content(ProcessSourceInput(content=content))
        if args.format == "xml":
            result = dicttoxml(
                result.model_dump(), custom_root="result", attr_type=False
            ).decode('utf-8')
        elif args.format == "json":
            result = result.model_dump_json()
        else:  # text
            result = result.content
        print(result)
    except Exception as e:
        logger.error(f"Error extracting content: {e}")
        sys.exit(1)


async def cclean_main():
    """CLI logic for cclean."""
    parser = argparse.ArgumentParser(
        description="Content Core CLI: Clean content string."
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging."
    )
    parser.add_argument(
        "content",
        nargs="?",
        help="Content to clean (URL, file path, text, JSON, or XML). If not provided, reads from stdin.",
    )

    args = parser.parse_args()

    # Adjust logging level based on debug flag using centralized configuration
    configure_logging(debug=args.debug)
    if args.debug:
        logger.debug("Debug logging enabled")

    content = get_content(args, parser)

    content = await process_input_content(content)
    content = parse_content_format(content)

    try:
        result = await cleanup_content(content)
        print(result)
    except Exception as e:
        logger.error(f"Error cleaning content: {e}")
        sys.exit(1)


async def csum_main():
    """CLI logic for csum."""
    parser = argparse.ArgumentParser(
        description="Content Core CLI: Summarize content with optional context."
    )
    parser.add_argument(
        "--context",
        default="",
        help="Optional context for summarization (e.g., 'summarize as if explaining to a child').",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logging."
    )
    parser.add_argument(
        "content",
        nargs="?",
        help="Content to summarize (URL, file path, text, JSON, or XML). If not provided, reads from stdin.",
    )

    args = parser.parse_args()

    # Adjust logging level based on debug flag using centralized configuration
    configure_logging(debug=args.debug)
    if args.debug:
        logger.debug("Debug logging enabled")

    content = get_content(args, parser)

    content = await process_input_content(content)
    content = parse_content_format(content)

    try:
        result = await summarize(content, args.context)
        print(result)
    except Exception as e:
        logger.error(f"Error summarizing content: {e}")
        sys.exit(1)


def ccore():
    """Synchronous wrapper for ccore."""
    asyncio.run(ccore_main())


def cclean():
    """Synchronous wrapper for cclean."""
    asyncio.run(cclean_main())


def csum():
    """Synchronous wrapper for csum."""
    asyncio.run(csum_main())


if __name__ == "__main__":
    ccore()
if __name__ == "__main__":
    ccore()
