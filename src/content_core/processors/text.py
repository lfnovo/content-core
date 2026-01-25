import asyncio
import re
from typing import Any, Dict

from markdownify import markdownify as md

from content_core.common import ProcessSourceState
from content_core.logging import logger


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


async def process_text_content(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Process text content - detect and convert HTML to markdown if present.

    This function handles "rendered markdown" - text that was copied from
    rendered views (like Obsidian reading mode, browser preview) that may
    contain HTML tags.

    Args:
        state: ProcessSourceState containing the content to process

    Returns:
        Dict with converted content if HTML was detected, empty dict otherwise
    """
    content = state.content
    if not content:
        return {}

    if detect_html(content):
        logger.debug("HTML detected in content, converting to markdown")
        try:
            converted = md(content, heading_style="ATX", bullets="-")
            return {"content": converted}
        except Exception as e:
            logger.warning(f"HTML conversion failed, keeping original content: {e}")
            return {}

    logger.debug("No HTML detected, keeping content as-is")
    return {}


async def extract_txt(state: ProcessSourceState) -> Dict[str, Any]:
    """
    Parse the text file and extract its content asynchronously.
    """
    return_dict: Dict[str, Any] = {}
    if state.file_path is not None and state.identified_type == "text/plain":
        logger.debug(f"Extracting text from {state.file_path}")
        file_path = state.file_path

        if file_path is not None:
            try:

                def _read_file():
                    with open(file_path, "r", encoding="utf-8") as file:
                        return file.read()

                # Run file I/O in thread pool
                content = await asyncio.get_event_loop().run_in_executor(
                    None, _read_file
                )

                logger.debug(f"Extracted: {content[:100]}")
                return_dict["content"] = content

            except FileNotFoundError:
                raise FileNotFoundError(f"File not found at {file_path}")
            except Exception as e:
                raise Exception(f"An error occurred: {e}")

    return return_dict
