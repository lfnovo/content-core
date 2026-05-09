"""E2E tests for Docling extraction — require docling installed and may download large models."""
from pathlib import Path

import pytest

from content_core.config import ContentCoreConfig
from content_core.extraction import extract_content

pytestmark = pytest.mark.e2e_heavy

FIXTURE_PATH = Path(__file__).parent.parent / "input_content"


@pytest.fixture
def pdf_file():
    path = FIXTURE_PATH / "file.pdf"
    if not path.exists():
        pytest.skip(f"Fixture file not found: {path}")
    return str(path)


@pytest.mark.asyncio
async def test_docling_pdf_extraction(pdf_file):
    """Test basic Docling PDF extraction with default settings."""
    config = ContentCoreConfig(document_engine="docling")
    result = await extract_content(file_path=pdf_file, config=config)

    assert result.source_type == "file"
    assert len(result.content) > 0
    assert "Buenos Aires" in result.content


@pytest.mark.asyncio
async def test_docling_with_formulas(pdf_file):
    """Test Docling extraction with formula enrichment enabled."""
    config = ContentCoreConfig(
        document_engine="docling",
        docling_formulas=True,
    )
    result = await extract_content(file_path=pdf_file, config=config)

    assert result.source_type == "file"
    assert len(result.content) > 0


@pytest.mark.asyncio
async def test_docling_with_vision(pdf_file):
    """Test Docling extraction with vision enrichment enabled (image description + charts)."""
    config = ContentCoreConfig(
        document_engine="docling",
        docling_vision=True,
    )
    result = await extract_content(file_path=pdf_file, config=config)

    assert result.source_type == "file"
    assert len(result.content) > 0
