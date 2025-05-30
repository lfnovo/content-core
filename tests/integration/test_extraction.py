from pathlib import Path

import pytest
from content_core.content.extraction import extract_content  # type: ignore


@pytest.fixture
def fixture_path():
    """Provides the path to the directory containing test input files."""
    return Path(__file__).parent.parent / "input_content"


@pytest.mark.asyncio
async def test_extract_content_from_text():
    """Tests content extraction from a raw text string."""
    input_data = {"content": "My sample content for testing."}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "text"
    assert "My sample content for testing." in result.content
    assert result.title == ""  # Or based on actual behavior


@pytest.mark.asyncio
async def test_extract_content_from_url(fixture_path):
    """Tests content extraction from a URL."""
    # Using a known URL from the notebook example
    input_data = {"url": "https://www.supernovalabs.com", "url_engine": "simple"}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    # Check for expected title and content snippets based on notebook output
    assert "Supernova Labs" in result.title
    assert "AI Consulting" in result.title
    # assert "Supernova Labs" in result.content
    # assert "AI Opportunity Map" in result.content  # Example snippet


@pytest.mark.asyncio
async def test_extract_content_from_url_firecrawl(fixture_path):
    """Tests content extraction from a URL."""
    try:
        import firecrawl
    except ImportError:
        pytest.skip("Firecrawl not installed")
    
    # Using a known URL from the notebook example
    input_data = {"url": "https://www.supernovalabs.com", "url_engine": "firecrawl"}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    # Check for expected title and content snippets based on notebook output
    assert "Supernova Labs" in result.title
    assert "AI Consulting" in result.title
    assert "Supernova Labs" in result.content
    assert "AI Opportunity Map" in result.content  # Example snippet


@pytest.mark.asyncio
async def test_extract_content_from_url_jina(fixture_path):
    """Tests content extraction from a URL."""
    # Using a known URL from the notebook example
    input_data = {"url": "https://www.supernovalabs.com", "url_engine": "jina"}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    # Check for expected title and content snippets based on notebook output
    assert "Supernova Labs" in result.title
    assert "AI Consulting" in result.title
    assert "Supernova Labs" in result.content
    assert "AI Opportunity Map" in result.content  # Example snippet


@pytest.mark.asyncio
async def test_extract_content_from_mp4(fixture_path):
    """Tests content extraction (transcript) from an MP4 file."""
    mp4_file = fixture_path / "file.mp4"
    # Ensure the user adds this file
    if not mp4_file.exists():
        pytest.skip(f"Fixture file not found: {mp4_file}")

    input_data = {"file_path": str(mp4_file)}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "file"
    assert result.title == "file.mp4"
    assert result.identified_type == "audio/mp3"  # Expect audio/mp3 after extraction
    assert "welcome" in result.content.lower()  # Check for expected word


@pytest.mark.asyncio
async def test_extract_content_from_mp3(fixture_path):
    """Tests content extraction (transcript) from an MP3 file."""
    mp3_file = fixture_path / "file.mp3"
    # Ensure the user adds this file
    if not mp3_file.exists():
        pytest.skip(f"Fixture file not found: {mp3_file}")

    input_data = {"file_path": str(mp3_file)}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "file"
    assert result.title == "file.mp3"
    assert result.identified_type == "audio/mpeg"  # Expect audio/mpeg after extraction
    assert "welcome" in result.content.lower()  # Check for expected word


@pytest.mark.asyncio
async def test_extract_content_from_markdown(fixture_path):
    """Tests content extraction from a Markdown file."""
    md_file = fixture_path / "file.md"
    # Ensure the user adds this file
    if not md_file.exists():
        pytest.skip(f"Fixture file not found: {md_file}")

    input_data = {"file_path": str(md_file)}
    result = await extract_content(input_data)

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

    input_data = {"file_path": str(epub_file)}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "file"
    assert result.title == "file.epub"
    assert (
        result.identified_type == "application/epub+zip"
    )  # Expect application/epub+zip for EPUB files
    assert "Wonderland" in result.content  # Check for expected text


@pytest.mark.asyncio
async def test_extract_content_from_youtube_url(fixture_path):
    """Tests extracting content from a YouTube URL."""
    # Use a different, more stable video URL
    youtube_url = "https://www.youtube.com/watch?v=pBy1zgt0XPc"
    result = await extract_content(dict(url=youtube_url))

    assert result.source_type == "url"
    assert result.identified_type == "youtube"  # Expect 'youtube' type
    assert "What is GitHub?" in result.title  # Check for expected title segment
    # Update keyword checks for the new video
    assert "github" in result.content.lower()
    assert "code" in result.content.lower()
    assert "git" in result.content.lower()  # Check for 'git'
    assert len(result.content) > 50  # Expecting a shorter transcript for this video


@pytest.mark.asyncio
async def test_extract_content_from_pdf(fixture_path):
    """Tests extracting content from a PDF file."""
    pdf_file = fixture_path / "file.pdf"
    if not pdf_file.exists():
        pytest.skip(f"Fixture file not found: {pdf_file}")

    result = await extract_content(dict(file_path=str(pdf_file)))

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

    result = await extract_content(dict(file_path=str(pptx_file)))

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

    result = await extract_content(dict(file_path=str(docx_file)))

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

    result = await extract_content(dict(file_path=str(xlsx_file), document_engine="simple"))

    assert result.source_type == "file"
    assert (
        result.identified_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert result.title is not None  # Attempt to extract title/metadata
    assert len(result.content) > 0  # Check that some content was extracted


# @pytest.mark.asyncio
# async def test_extract_content_from_xlsx_docling(fixture_path):
#     """Tests extracting content from a XLSX file using docling engine."""
#     xlsx_file = fixture_path / "file.xlsx"
#     if not xlsx_file.exists():
#         pytest.skip(f"Fixture file not found: {xlsx_file}")

#     result = await extract_content(dict(file_path=str(xlsx_file), document_engine="docling"))

#     assert result.source_type == "file"
#     assert (
#         result.identified_type
#         == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )
#     assert result.title is not None  # Attempt to extract title/metadata
#     assert len(result.content) > 0  # Check that some content was extracted


@pytest.mark.asyncio
async def test_extract_content_from_pdf_url():
    """Tests extracting content from a remote PDF URL."""
    url = "https://arxiv.org/pdf/2408.09869"
    result = await extract_content({"url": url})
    assert result.source_type == "url"
    assert result.identified_type == "application/pdf"
    assert len(result.content) > 100  # Expect substantial extracted text
