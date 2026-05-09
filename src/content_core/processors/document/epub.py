"""EPUB extraction using fast-ebook."""
import asyncio

from fast_ebook.epub import read_epub

from content_core.config import ContentCoreConfig
from content_core.logging import logger
from content_core.common.state import ExtractionOutput

SUPPORTED_EPUB_TYPES = ["application/epub+zip"]


async def extract_epub_file(file_path: str, config: ContentCoreConfig) -> ExtractionOutput:
    """Extract content from an EPUB file using fast-ebook."""
    def _extract():
        logger.debug(f"Extracting EPUB: {file_path}")
        epub = read_epub(file_path)
        return epub.to_markdown()

    try:
        text = await asyncio.get_event_loop().run_in_executor(None, _extract)
        return ExtractionOutput(
            content=text or "",
            source_type="file",
            identified_type="application/epub+zip",
        )
    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"EPUB extraction failed for {file_path}") from e
