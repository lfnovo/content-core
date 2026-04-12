from pathlib import Path

import pytest
from content_core.config import ContentCoreConfig
from content_core.extraction import extract_content


@pytest.fixture
def fixture_path():
    """Provides the path to the directory containing test input files."""
    return Path(__file__).parent.parent / "input_content"


@pytest.mark.asyncio
async def test_extract_content_from_text():
    """Tests content extraction from a raw text string."""
    result = await extract_content(content="My sample content for testing.")

    assert hasattr(result, "source_type")
    assert result.source_type == "text"
    assert "My sample content for testing." in result.content
    assert result.title == ""  # Or based on actual behavior


@pytest.mark.asyncio
async def test_extract_content_from_html_text():
    """Tests that HTML content is converted to markdown."""
    html_content = "<h1>Title</h1><p>This is <strong>bold</strong> text.</p>"
    result = await extract_content(content=html_content)

    assert result.source_type == "text"
    assert "# Title" in result.content  # H1 becomes markdown header
    assert "**bold**" in result.content  # Strong becomes bold
    assert "<h1>" not in result.content  # HTML tags removed
    assert "<p>" not in result.content
    assert "<strong>" not in result.content


@pytest.mark.asyncio
async def test_extract_content_from_plain_text_unchanged():
    """Tests that plain text without HTML is unchanged."""
    plain_content = "Just some plain text without any formatting."
    result = await extract_content(content=plain_content)

    assert result.source_type == "text"
    assert result.content == plain_content  # Content unchanged


@pytest.mark.asyncio
async def test_extract_content_from_html_list():
    """Tests that HTML lists are converted to markdown."""
    html_content = "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>"
    result = await extract_content(content=html_content)

    assert result.source_type == "text"
    assert "- Item 1" in result.content
    assert "- Item 2" in result.content
    assert "- Item 3" in result.content
    assert "<ul>" not in result.content
    assert "<li>" not in result.content


@pytest.mark.asyncio
async def test_extract_content_from_html_links():
    """Tests that HTML links are converted to markdown."""
    html_content = '<p>Visit <a href="https://example.com">our site</a> for more.</p>'
    result = await extract_content(content=html_content)

    assert result.source_type == "text"
    assert "[our site](https://example.com)" in result.content
    assert "<a " not in result.content


@pytest.mark.asyncio
async def test_extract_content_html_detection_threshold():
    """Tests that single HTML tag doesn't trigger conversion (threshold is 2)."""
    # Single tag - should NOT convert
    single_tag_content = "Hello <br> World"
    result = await extract_content(content=single_tag_content)

    assert result.source_type == "text"
    # Content should be unchanged since only 1 tag
    assert result.content == single_tag_content


@pytest.mark.asyncio
async def test_extract_content_from_markdown(fixture_path):
    """Tests content extraction from a Markdown file."""
    md_file = fixture_path / "file.md"
    # Ensure the user adds this file
    if not md_file.exists():
        pytest.skip(f"Fixture file not found: {md_file}")

    result = await extract_content(file_path=str(md_file))

    assert hasattr(result, "source_type")
    assert result.source_type == "file"
    assert result.title == "file.md"
    assert result.identified_type == "text/plain"  # Expect text/plain for MD files
    assert "Buenos Aires" in result.content  # Check for expected text


@pytest.mark.asyncio
async def test_extract_content_from_epub(fixture_path):
    """Tests content extraction from an EPUB file."""
    epub_file = fixture_path / "file.epub"
    # Ensure the user adds this file
    if not epub_file.exists():
        pytest.skip(f"Fixture file not found: {epub_file}")

    result = await extract_content(file_path=str(epub_file))

    assert hasattr(result, "source_type")
    assert result.source_type == "file"
    assert result.title == "file.epub"
    assert (
        result.identified_type == "application/epub+zip"
    )  # Expect application/epub+zip for EPUB files
    assert "Wonderland" in result.content  # Check for expected text


@pytest.mark.asyncio
async def test_extract_content_from_pdf(fixture_path):
    """Tests extracting content from a PDF file."""
    pdf_file = fixture_path / "file.pdf"
    if not pdf_file.exists():
        pytest.skip(f"Fixture file not found: {pdf_file}")

    result = await extract_content(file_path=str(pdf_file))

    assert result.source_type == "file"
    assert result.identified_type == "application/pdf"
    assert "Buenos Aires" in result.content  # Check for expected text
    assert result.title is not None  # Attempt to extract title/metadata
    assert len(result.content) > 0  # Check that some content was extracted


@pytest.mark.asyncio
async def test_extract_content_from_pptx(fixture_path):
    """Tests extracting content from a PPTX file."""
    pptx_file = fixture_path / "file.pptx"
    if not pptx_file.exists():
        pytest.skip(f"Fixture file not found: {pptx_file}")

    result = await extract_content(file_path=str(pptx_file))

    assert result.source_type == "file"
    assert (
        result.identified_type
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert "MASTERNODE" in result.content  # Check for expected text
    assert result.title is not None  # Attempt to extract title/metadata
    assert len(result.content) > 0  # Check that some content was extracted


@pytest.mark.asyncio
async def test_extract_content_from_docx(fixture_path):
    """Tests extracting content from a DOCX file."""
    docx_file = fixture_path / "file.docx"
    if not docx_file.exists():
        pytest.skip(f"Fixture file not found: {docx_file}")

    result = await extract_content(file_path=str(docx_file))

    assert result.source_type == "file"
    assert (
        result.identified_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "Buenos Aires" in result.content  # Check for expected text
    assert result.title is not None  # Attempt to extract title/metadata
    assert len(result.content) > 0  # Check that some content was extracted


@pytest.mark.asyncio
async def test_extract_content_from_xlsx(fixture_path):
    """Tests extracting content from a XLSX file."""
    xlsx_file = fixture_path / "file.xlsx"
    if not xlsx_file.exists():
        pytest.skip(f"Fixture file not found: {xlsx_file}")

    result = await extract_content(
        file_path=str(xlsx_file),
        config=ContentCoreConfig(document_engine="simple"),
    )

    assert result.source_type == "file"
    assert (
        result.identified_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert result.title is not None  # Attempt to extract title/metadata
    assert len(result.content) > 0  # Check that some content was extracted
