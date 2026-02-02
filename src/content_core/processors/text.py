import asyncio
import re
from typing import Any, Dict, Optional

from markdownify import markdownify as md

from content_core.common import ProcessSourceState
from content_core.processors.base import Processor, ProcessorResult, Source
from content_core.processors.registry import processor
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


# =============================================================================
# New Processor API (v2.0)
# =============================================================================


@processor(
    name="text",
    mime_types=[
        "text/plain",
        "text/markdown",
        "text/x-markdown",
    ],
    extensions=[".txt", ".md", ".markdown", ".text"],
    priority=50,
    requires=[],
    category="documents",
)
class TextProcessor(Processor):
    """Plain text file extraction processor.

    Reads text files and optionally converts HTML content to markdown.
    """

    @classmethod
    def is_available(cls) -> bool:
        """Text processor is always available."""
        return True

    async def extract(
        self, source: Source, options: Optional[Dict[str, Any]] = None
    ) -> ProcessorResult:
        """Extract content from text file or raw content.

        Args:
            source: The Source to extract content from.
            options: Optional extraction options.

        Returns:
            ProcessorResult with extracted content.
        """
        content = ""

        if source.file_path:
            # Read from file
            state = ProcessSourceState(
                file_path=source.file_path,
                identified_type=source.mime_type or "text/plain",
            )
            result = await extract_txt(state)
            content = result.get("content", "")

        elif source.content:
            # Process raw content
            if isinstance(source.content, bytes):
                content = source.content.decode("utf-8", errors="replace")
            else:
                content = source.content

            # Check for HTML and convert if needed
            state = ProcessSourceState(content=content)
            result = await process_text_content(state)
            if result.get("content"):
                content = result["content"]

        return ProcessorResult(
            content=content,
            mime_type=source.mime_type or "text/plain",
            metadata={
                "extraction_engine": "text",
            },
        )
