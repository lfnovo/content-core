"""Tests for the v2 extraction orchestrator routing logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from content_core.common.exceptions import InvalidInputError, UnsupportedTypeException
from content_core.config import ContentCoreConfig
from content_core.extraction import extract_content
from content_core.common.state import ExtractionOutput


def _make_output(**kwargs) -> ExtractionOutput:
    """Helper to create a minimal ExtractionOutput."""
    defaults = {"content": "test content", "source_type": "file", "identified_type": ""}
    defaults.update(kwargs)
    return ExtractionOutput(**defaults)


# ---------------------------------------------------------------------------
# 1. Text input -> process_text
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_text_input_calls_process_text():
    expected = _make_output(source_type="text")
    with patch(
        "content_core.extraction.process_text", new_callable=AsyncMock, return_value=expected
    ) as mock:
        result = await extract_content(content="hello")
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 2. YouTube URL -> extract_youtube
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_youtube_url_calls_extract_youtube():
    expected = _make_output(source_type="url", identified_type="youtube")
    with patch(
        "content_core.extraction.extract_youtube", new_callable=AsyncMock, return_value=expected
    ) as mock:
        result = await extract_content(url="https://www.youtube.com/watch?v=abc")
        mock.assert_awaited_once()
        assert result is expected


@pytest.mark.asyncio
async def test_youtu_be_url_calls_extract_youtube():
    expected = _make_output(source_type="url", identified_type="youtube")
    with patch(
        "content_core.extraction.extract_youtube", new_callable=AsyncMock, return_value=expected
    ) as mock:
        result = await extract_content(url="https://youtu.be/abc")
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 3. Regular URL with article MIME -> extract_from_url
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_url_article_calls_extract_from_url():
    expected = _make_output(source_type="url", identified_type="article")
    with patch(
        "content_core.extraction.detect_remote_mime",
        new_callable=AsyncMock,
        return_value="article",
    ), patch(
        "content_core.extraction.extract_from_url",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_extract:
        result = await extract_content(url="https://example.com/article")
        mock_extract.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 4. URL with PDF MIME -> download + extract_pdf_file
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_url_pdf_downloads_and_calls_extract_pdf():
    expected = _make_output(source_type="file", identified_type="application/pdf")
    with patch(
        "content_core.extraction.detect_remote_mime",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ), patch(
        "content_core.extraction._download_remote_file",
        new_callable=AsyncMock,
        return_value="/tmp/fake.pdf",
    ) as mock_download, patch(
        "content_core.extraction._extract_file",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_extract_file:
        result = await extract_content(url="https://example.com/doc.pdf")
        mock_download.assert_awaited_once()
        mock_extract_file.assert_awaited_once()
        # source_type should be overridden to "url"
        assert result.source_type == "url"


# ---------------------------------------------------------------------------
# 5. File with PDF MIME -> extract_pdf_file
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_file_pdf_calls_extract_pdf_file():
    expected = _make_output(identified_type="application/pdf")
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ), patch(
        "content_core.extraction.extract_pdf_file",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock:
        result = await extract_content(file_path="/tmp/test.pdf", config=cfg)
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 5b. File with EPUB MIME -> extract_epub_file
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_file_epub_calls_extract_epub_file():
    expected = _make_output(identified_type="application/epub+zip")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/epub+zip",
    ), patch(
        "content_core.extraction.extract_epub_file",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock:
        result = await extract_content(file_path="/tmp/test.epub")
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 6. File with DOCX MIME -> extract_office
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_file_docx_calls_extract_office():
    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    expected = _make_output(identified_type=mime)
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value=mime,
    ), patch(
        "content_core.extraction.extract_office",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock:
        result = await extract_content(file_path="/tmp/test.docx", config=cfg)
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 7. File with video/* MIME -> extract_video
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_file_video_calls_extract_video():
    expected = _make_output(identified_type="video/mp4")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="video/mp4",
    ), patch(
        "content_core.extraction.extract_video",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock:
        result = await extract_content(file_path="/tmp/test.mp4")
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 8. File with audio/* MIME -> transcribe_audio
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_file_audio_calls_transcribe_audio():
    expected = _make_output(identified_type="audio/mp3")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="audio/mp3",
    ), patch(
        "content_core.extraction.transcribe_audio",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock:
        result = await extract_content(file_path="/tmp/test.mp3")
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 9. File with text/plain MIME -> extract_text_file
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_file_text_calls_extract_text_file():
    expected = _make_output(identified_type="text/plain")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="text/plain",
    ), patch(
        "content_core.extraction.extract_text_file",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock:
        result = await extract_content(file_path="/tmp/test.txt")
        mock.assert_awaited_once()
        assert result is expected


# ---------------------------------------------------------------------------
# 10. No source -> InvalidInputError
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_source_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        await extract_content()


# ---------------------------------------------------------------------------
# 11. Unknown file MIME -> UnsupportedTypeException
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unknown_mime_raises_unsupported():
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/x-unknown-binary",
    ):
        with pytest.raises(UnsupportedTypeException):
            await extract_content(file_path="/tmp/test.bin")


# ---------------------------------------------------------------------------
# 12. Config is passed through to processors
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_config_passed_to_processor():
    custom_cfg = ContentCoreConfig(url_engine="firecrawl")
    expected = _make_output(source_type="text")
    with patch(
        "content_core.extraction.process_text", new_callable=AsyncMock, return_value=expected
    ) as mock:
        await extract_content(content="hello", config=custom_cfg)
        # Verify the custom config was passed
        # process_text is called positionally: process_text(content, cfg)
        args = mock.call_args[0]
        assert args[1] is custom_cfg


# ---------------------------------------------------------------------------
# 13. Docling flags warning without docling engine
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_docling_flags_warning_without_engine():
    """Warning should be logged when docling flags set but engine is not docling."""
    cfg = ContentCoreConfig(docling_formulas=True, document_engine="simple")

    with patch("content_core.extraction.extract_pdf_file", new_callable=AsyncMock) as mock_pdf, \
         patch("content_core.content.identification.get_file_type", new_callable=AsyncMock) as mock_type, \
         patch("content_core.extraction.logger") as mock_logger:
        mock_type.return_value = "application/pdf"
        mock_pdf.return_value = ExtractionOutput(content="text")

        result = await extract_content(file_path="/tmp/test.pdf", config=cfg)

        mock_logger.warning.assert_called_once()
        assert "docling" in mock_logger.warning.call_args[0][0].lower()
