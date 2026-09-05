import asyncio
import html
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


# A document that opens with a doctype or <html> tag is HTML regardless of how
# many structural tags its body has (a one-paragraph page is still a page).
HTML_DOCUMENT_START = re.compile(r"[\s\ufeff]*(?:<!--.*?-->\s*)*<(?:!doctype\s+html|html)\b", re.IGNORECASE | re.DOTALL)

# Declared charset in an HTML head, used only when the file is not valid UTF-8.
HTML_CHARSET_RE = re.compile(rb"<meta[^>]+charset\s*=\s*[\"']?\s*([\w.:-]+)", re.IGNORECASE)


def _decode_text_file(raw: bytes) -> str:
    """Decode a text/HTML file: UTF-16 by BOM, then strict UTF-8 (BOM stripped),
    then the declared charset, then cp1252 (superset of latin-1, the usual legacy
    encoding) with replacement."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    match = HTML_CHARSET_RE.search(raw[:4096])
    if match:
        codec = match.group(1).decode("ascii", "ignore")
        try:
            return raw.decode(codec, errors="replace")
        except LookupError:
            logger.debug(f"Unknown declared charset {codec!r}, falling back to cp1252")
    return raw.decode("cp1252", errors="replace")


def detect_html(content: str) -> bool:
    """
    Detect if content contains meaningful HTML structure.

    Args:
        content: Text content to analyze

    Returns:
        True if at least HTML_DETECTION_THRESHOLD structural tags are found
    """
    if HTML_DOCUMENT_START.match(content):
        return True
    matches = HTML_STRUCTURAL_TAGS.findall(content)
    return len(matches) >= HTML_DETECTION_THRESHOLD


TITLE_RE = re.compile(
    r"<title[^>]*>(.*?)</title>",
    re.IGNORECASE | re.DOTALL,
)

# <head> carries metadata (title, scripts, styles) that markdownify would
# otherwise render as text at the top of the body.
HEAD_RE = re.compile(r"<head[^>]*>.*?</head>", re.IGNORECASE | re.DOTALL)


def extract_html_title(content: str) -> str:
    """Extract the HTML document title."""
    match = TITLE_RE.search(content)
    if not match:
        return ""

    return html.unescape(match.group(1)).strip()


def strip_html_head(content: str) -> str:
    """Remove the <head>...</head> block so its contents don't leak into the body."""
    return HEAD_RE.sub("", content, count=1)


async def extract_text_file(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content from a plain text file."""

    def _read_file():
        with open(file_path, "rb") as file:
            return _decode_text_file(file.read())

    try:
        content = await asyncio.get_event_loop().run_in_executor(None, _read_file)
        logger.debug(f"Extracted text from {file_path}: {content[:100]}")
        result = await process_text(content, config)
        result.source_type = "file"
        return result
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
            title = extract_html_title(content)
            converted = md(strip_html_head(content), heading_style="ATX", bullets="-")
            return ExtractionOutput(
                content=converted,
                title=title,
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
