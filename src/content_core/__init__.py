"""Content Core — Extract and summarize content from any source."""
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from content_core.config import ContentCoreConfig
from content_core.content.summary import summarize
from content_core.extraction import check_file_support, extract_content
from content_core.logging import configure_logging
from content_core.common.state import ExtractionInput, ExtractionOutput, FileSupport

# Convenience alias
extract = extract_content

# Libraries must not configure logging — loguru's logger is a process-wide
# singleton. Stay silent by default; applications opt in via
# `logger.enable("content_core")` or `content_core.configure_logging()`.
logger.disable("content_core")

__all__ = [
    "configure_logging",
    "extract_content",
    "extract",
    "check_file_support",
    "summarize",
    "ContentCoreConfig",
    "ExtractionInput",
    "ExtractionOutput",
    "FileSupport",
]
