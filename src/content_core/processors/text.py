import asyncio
import re

from markdownify import markdownify as md

from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput


# Minimum number of structural HTML tags required to trigger conversion
# A threshold of 2 avoids false positives from stray tags like a single <br>
HTML_DETECTION_THRESHOLD = 2

# HTML tags that indicate meaningful structure
HTML_STRUCTURAL_TAGS = re.compile(
    r"<(p|div|h[1-6]|ul|ol|li|strong|em|b|i|a|code|pre|blockquote|table|thead|tbody|tr|td|th|article|section|header|footer|nav|span|br)[^>]*>",
    re.IGNORECASE,
)


def detect_html(content: str) -> bool:
    """
    Detect if content contains meaningful HTML structure.

    Args:
        content: Text content to analyze

    Returns:
        True if at least HTML_DETECTION_THRESHOLD structural tags are found
    """
    matches = HTML_STRUCTURAL_TAGS.findall(content)
    return len(matches) >= HTML_DETECTION_THRESHOLD


async def extract_text_file(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content from a plain text file."""

    def _read_file():
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    try:
        content = await asyncio.get_event_loop().run_in_executor(None, _read_file)
        logger.debug(f"Extracted text from {file_path}: {content[:100]}")
        return ExtractionOutput(
            content=content,
            source_type="file",
            identified_type="text/plain",
        )
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found at {file_path}")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")


async def process_text(content: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Process text content -- detect and convert HTML to markdown if present."""
    if not content:
        return ExtractionOutput(
            content=content,
            source_type="text",
            identified_type="text/plain",
        )

    if detect_html(content):
        logger.debug("HTML detected in content, converting to markdown")
        try:
            converted = md(content, heading_style="ATX", bullets="-")
            return ExtractionOutput(
                content=converted,
                source_type="text",
                identified_type="text/plain",
            )
        except Exception as e:
            logger.warning(f"HTML conversion failed, keeping original content: {e}")

    logger.debug("No HTML detected, keeping content as-is")
    return ExtractionOutput(
        content=content,
        source_type="text",
        identified_type="text/plain",
    )
