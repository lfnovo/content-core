"""Content Core — Extract and summarize content from any source."""
from dotenv import load_dotenv

load_dotenv()

from content_core.config import ContentCoreConfig
from content_core.content.summary import summarize
from content_core.extraction import extract_content
from content_core.logging import configure_logging
from content_core.common.state import ExtractionInput, ExtractionOutput

# Convenience alias
extract = extract_content

# Configure default logging
configure_logging(debug=False)

__all__ = [
    "extract_content",
    "extract",
    "summarize",
    "ContentCoreConfig",
    "ExtractionInput",
    "ExtractionOutput",
]
