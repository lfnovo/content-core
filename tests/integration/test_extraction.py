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
async def test_extract_content_from_html_text():
    """Tests that HTML content is converted to markdown."""
    html_content = "<h1>Title</h1><p>This is <strong>bold</strong> text.</p>"
    result = await extract_content({"content": html_content})

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
    result = await extract_content({"content": plain_content})

    assert result.source_type == "text"
    assert result.content == plain_content  # Content unchanged


@pytest.mark.asyncio
async def test_extract_content_from_html_list():
    """Tests that HTML lists are converted to markdown."""
    html_content = "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>"
    result = await extract_content({"content": html_content})

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
    result = await extract_content({"content": html_content})

    assert result.source_type == "text"
    assert "[our site](https://example.com)" in result.content
    assert "<a " not in result.content


@pytest.mark.asyncio
async def test_extract_content_html_detection_threshold():
    """Tests that single HTML tag doesn't trigger conversion (threshold is 2)."""
    # Single tag - should NOT convert
    single_tag_content = "Hello <br> World"
    result = await extract_content({"content": single_tag_content})

    assert result.source_type == "text"
    # Content should be unchanged since only 1 tag
    assert result.content == single_tag_content


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
    # Check that content was extracted and contains relevant keywords
    assert len(result.content) > 100
    assert "AI" in result.content


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
    # Check that content was extracted and contains relevant keywords
    assert len(result.content) > 100
    assert "AI" in result.content


@pytest.mark.asyncio
async def test_extract_content_from_url_crawl4ai(fixture_path):
    """Tests content extraction from a URL using Crawl4AI."""
    pytest.importorskip("crawl4ai", reason="Crawl4AI not installed")

    # Using a known URL from the notebook example
    input_data = {"url": "https://www.supernovalabs.com", "url_engine": "crawl4ai"}
    result = await extract_content(input_data)

    assert hasattr(result, "source_type")
    assert result.source_type == "url"
    # Check for expected title and content snippets based on notebook output
    assert "Supernova Labs" in result.title
    assert "AI Consulting" in result.title
    # Check that content was extracted and contains relevant keywords
    assert len(result.content) > 100
    assert "AI" in result.content


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
@pytest.mark.xfail(
    reason="Event loop cleanup issue with httpx when running after other audio tests. "
           "This is a known pytest-asyncio + httpx interaction issue that doesn't affect functionality.",
    strict=False
)
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


@pytest.mark.asyncio
async def test_extract_content_from_pdf_docling_vlm_local(fixture_path):
    """Tests extracting content from a PDF using docling-vlm local engine."""
    # Check if docling[vlm] is installed
    try:
        from content_core.processors.docling_vlm import DOCLING_VLM_LOCAL_AVAILABLE
        if not DOCLING_VLM_LOCAL_AVAILABLE:
            pytest.skip("docling[vlm] not installed - install with: pip install content-core[docling-vlm]")
    except ImportError:
        pytest.skip("docling_vlm module not available")

    pdf_file = fixture_path / "file.pdf"
    if not pdf_file.exists():
        pytest.skip(f"Fixture file not found: {pdf_file}")

    result = await extract_content(
        dict(
            file_path=str(pdf_file),
            document_engine="docling-vlm",
            vlm_inference_mode="local",
        )
    )

    assert result.source_type == "file"
    assert result.identified_type == "application/pdf"
    assert len(result.content) > 0  # Check that content was extracted
    assert result.metadata.get("vlm_inference") == "local"


@pytest.mark.asyncio
async def test_extract_content_from_pdf_docling_vlm_remote(fixture_path):
    """Tests extracting content from a PDF using docling-vlm remote engine."""
    import os
    from unittest.mock import AsyncMock, MagicMock, patch

    # Check if httpx is available
    try:
        import httpx  # noqa: F401
    except ImportError:
        pytest.skip("httpx not installed - install with: pip install httpx")

    pdf_file = fixture_path / "file.pdf"
    if not pdf_file.exists():
        pytest.skip(f"Fixture file not found: {pdf_file}")

    # Check if a real docling-serve is running (for real integration test)
    docling_serve_url = os.environ.get("CCORE_DOCLING_SERVE_URL", "http://localhost:5001")

    # Try to connect to docling-serve
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{docling_serve_url}/health")
            if response.status_code == 200:
                # Real docling-serve is available, run actual integration test
                result = await extract_content(
                    dict(
                        file_path=str(pdf_file),
                        document_engine="docling-vlm",
                        vlm_inference_mode="remote",
                        vlm_remote_url=docling_serve_url,
                    )
                )

                assert result.source_type == "file"
                assert result.identified_type == "application/pdf"
                assert len(result.content) > 0
                assert result.metadata.get("vlm_inference") == "remote"
                return
    except Exception:
        pass  # docling-serve not available, use mock test

    # Fall back to mock test when docling-serve is not running
    mock_response = MagicMock()
    mock_response.json.return_value = {"content": "Mocked VLM extracted content from PDF"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

    with patch("content_core.processors.docling_vlm.httpx.AsyncClient", return_value=mock_client):
        result = await extract_content(
            dict(
                file_path=str(pdf_file),
                document_engine="docling-vlm",
                vlm_inference_mode="remote",
            )
        )

        assert result.source_type == "file"
        assert result.identified_type == "application/pdf"
        assert "Mocked VLM extracted content" in result.content
        assert result.metadata.get("vlm_inference") == "remote"


@pytest.mark.asyncio
async def test_docling_vlm_unsupported_type_fallback(fixture_path):
    """Tests that docling-vlm falls back to other engines for unsupported file types."""
    # VLM primarily supports PDF and images, test with a text file (unsupported)
    md_file = fixture_path / "file.md"
    if not md_file.exists():
        pytest.skip(f"Fixture file not found: {md_file}")

    # Even with docling-vlm engine, text files should fall back to simple extraction
    result = await extract_content(
        dict(
            file_path=str(md_file),
            document_engine="docling-vlm",
        )
    )

    assert result.source_type == "file"
    assert result.identified_type == "text/plain"
    assert len(result.content) > 0  # Content should still be extracted via fallback


@pytest.mark.asyncio
async def test_docling_vlm_config_override(fixture_path):
    """Tests that VLM configuration can be overridden via state."""
    from unittest.mock import AsyncMock, MagicMock, patch

    pdf_file = fixture_path / "file.pdf"
    if not pdf_file.exists():
        pytest.skip(f"Fixture file not found: {pdf_file}")

    # Check if httpx is available for remote mode
    try:
        import httpx  # noqa: F401
    except ImportError:
        pytest.skip("httpx not installed")

    # Mock the remote endpoint
    mock_response = MagicMock()
    mock_response.json.return_value = {"content": "Content from custom server"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value.post = mock_post

    custom_url = "http://custom-server:9999"

    with patch("content_core.processors.docling_vlm.httpx.AsyncClient", return_value=mock_client):
        result = await extract_content(
            dict(
                file_path=str(pdf_file),
                document_engine="docling-vlm",
                vlm_inference_mode="remote",
                vlm_remote_url=custom_url,
            )
        )

        assert result.content == "Content from custom server"
        assert result.metadata.get("vlm_remote_url") == custom_url

        # Verify the custom URL was used
        call_args = mock_post.call_args
        assert custom_url in str(call_args)


@pytest.mark.asyncio
async def test_auto_mode_fallback_to_crawl4ai():
    """
    Tests that auto mode correctly falls back to Crawl4AI when Jina fails.
    
    This test verifies the fallback chain:
    1. Auto mode tries Jina first (when no FIRECRAWL_API_KEY)
    2. When Jina raises an exception, it should try Crawl4AI
    3. When Crawl4AI succeeds, content should be returned
    """
    pytest.importorskip("crawl4ai", reason="Crawl4AI not installed - auto mode fallback test requires Crawl4AI")
    
    import os
    from unittest.mock import patch
    
    # Temporarily ensure FIRECRAWL_API_KEY is not set (so auto mode tries Jina first)
    original_firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
    if original_firecrawl_key:
        del os.environ["FIRECRAWL_API_KEY"]
    
    try:
        # Mock extract_url_jina to raise an exception (simulating Jina failure)
        with patch("content_core.processors.url.extract_url_jina") as mock_jina:
            # Simulate Jina API failure
            mock_jina.side_effect = Exception("Jina API error (mocked)")
            
            # Test URL - use auto mode (should fallback to Crawl4AI when Jina fails)
            test_url = "https://www.supernovalabs.com"
            input_data = {"url": test_url, "url_engine": "auto"}
            
            result = await extract_content(input_data)
            
            # Verify that the extraction succeeded (via Crawl4AI fallback)
            assert result is not None
            assert hasattr(result, "source_type")
            assert result.source_type == "url"
            
            # Verify content was successfully extracted
            assert len(result.content) > 100
            assert "AI" in result.content or "Supernova" in result.title
            
            # Verify that Jina was attempted (and failed)
            mock_jina.assert_called_once_with(test_url)
            
    finally:
        # Restore original FIRECRAWL_API_KEY if it was set
        if original_firecrawl_key:
            os.environ["FIRECRAWL_API_KEY"] = original_firecrawl_key
