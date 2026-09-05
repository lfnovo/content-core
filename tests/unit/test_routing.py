"""Tests for the v2 extraction orchestrator routing logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from content_core.common.exceptions import (
    ConfigurationError,
    InvalidInputError,
    UnsupportedTypeException,
)
from content_core.config import ContentCoreConfig
from content_core.extraction import _route_for_mime, check_file_support, extract_content
from content_core.common.state import ExtractionOutput, FileSupport


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
# 2b. Reddit URL -> extract_reddit
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reddit_url_calls_extract_reddit():
    expected = _make_output(source_type="url", identified_type="reddit")
    with patch(
        "content_core.extraction.extract_reddit", new_callable=AsyncMock, return_value=expected
    ) as mock:
        result = await extract_content(
            url="https://www.reddit.com/r/python/comments/abc123/some_post/"
        )
        mock.assert_awaited_once()
        assert result is expected


@pytest.mark.asyncio
async def test_reddit_fallback_on_failure():
    """When Reddit JSON extraction fails, falls back to normal URL extraction."""
    fallback = _make_output(source_type="url", identified_type="article")
    with patch(
        "content_core.extraction.extract_reddit",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "content_core.extraction.detect_remote_mime",
        new_callable=AsyncMock,
        return_value="article",
    ), patch(
        "content_core.extraction.extract_from_url",
        new_callable=AsyncMock,
        return_value=fallback,
    ) as mock_url:
        result = await extract_content(
            url="https://www.reddit.com/r/python/comments/abc123/some_post/"
        )
        mock_url.assert_awaited_once()
        assert result.identified_type == "article"


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

        await extract_content(file_path="/tmp/test.pdf", config=cfg)

        mock_logger.warning.assert_called_once()
        assert "docling" in mock_logger.warning.call_args[0][0].lower()


# ---------------------------------------------------------------------------
# 14. check_file_support pre-flight verdict
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_file_support_supported():
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ):
        result = await check_file_support("/tmp/test.pdf", config=cfg)
    assert isinstance(result, FileSupport)
    assert result.supported is True
    assert result.identified_type == "application/pdf"
    assert result.processor == "pdf"
    assert result.reason is None
    assert result.document_engine == "simple"
    assert result.file_path == "/tmp/test.pdf"


@pytest.mark.asyncio
async def test_check_file_support_unsupported():
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/x-unknown-binary",
    ):
        result = await check_file_support("/tmp/test.bin", config=cfg)
    assert result.supported is False
    assert result.processor is None
    assert result.reason is not None
    assert "application/x-unknown-binary" in result.reason


@pytest.mark.asyncio
async def test_check_file_support_unidentifiable_returns_verdict():
    """A file whose type can't be determined is a verdict, not a raised error."""
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        side_effect=UnsupportedTypeException("Unable to determine file type for: x"),
    ):
        result = await check_file_support("/tmp/mystery.xyz", config=cfg)
    assert result.supported is False
    assert result.processor is None
    assert result.identified_type == ""
    assert "determine file type" in result.reason


@pytest.mark.asyncio
async def test_check_file_support_does_not_extract():
    """The pre-flight check must never invoke a real extractor."""
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ), patch(
        "content_core.extraction.extract_pdf_file", new_callable=AsyncMock
    ) as mock_pdf:
        await check_file_support("/tmp/test.pdf", config=cfg)
        mock_pdf.assert_not_awaited()


@pytest.mark.asyncio
async def test_check_file_support_agrees_with_extraction():
    """The verdict must never disagree with what extract_content actually does."""
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/x-unknown-binary",
    ):
        verdict = await check_file_support("/tmp/test.bin", config=cfg)
        assert verdict.supported is False
        # extraction of the same type raises, confirming the verdict
        with pytest.raises(UnsupportedTypeException):
            await extract_content(file_path="/tmp/test.bin", config=cfg)


# ---------------------------------------------------------------------------
# 15. text/html routes to the text processor on the simple/no-docling path
# ---------------------------------------------------------------------------
def test_route_for_mime_html_goes_to_text():
    cfg = ContentCoreConfig(document_engine="simple")
    assert _route_for_mime("text/html", cfg) == "text"


@pytest.mark.asyncio
async def test_file_html_calls_extract_text_file():
    expected = _make_output(identified_type="text/html")
    cfg = ContentCoreConfig(document_engine="simple")
    with patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="text/html",
    ), patch(
        "content_core.extraction.extract_text_file",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock:
        result = await extract_content(file_path="/tmp/page.html", config=cfg)
        mock.assert_awaited_once()
        assert result is expected
        assert result.identified_type == "text/html"


@pytest.mark.asyncio
async def test_check_file_support_html_file(tmp_path):
    page = tmp_path / "page.html"
    page.write_text("<html><head><title>T</title></head><body><p>Hi</p></body></html>")
    cfg = ContentCoreConfig(document_engine="simple")
    result = await check_file_support(str(page), config=cfg)
    assert result.supported is True
    assert result.identified_type == "text/html"
    assert result.processor == "text"


# ---------------------------------------------------------------------------
# 16. Explicit document_engine="docling" with docling not installed
# ---------------------------------------------------------------------------
def _docling_missing():
    """Patch the orchestrator's view of docling to "not installed"."""
    return patch.multiple(
        "content_core.extraction",
        DOCLING_AVAILABLE=False,
        extract_docling=None,
    )


def _docling_installed(mock_extract):
    """Patch the orchestrator's view of docling to "installed"."""
    return patch.multiple(
        "content_core.extraction",
        DOCLING_AVAILABLE=True,
        extract_docling=mock_extract,
    )


def test_route_for_mime_explicit_docling_missing_raises():
    cfg = ContentCoreConfig(document_engine="docling")
    with _docling_missing():
        with pytest.raises(ConfigurationError) as exc_info:
            _route_for_mime("application/pdf", cfg)
    message = str(exc_info.value)
    assert "pip install content-core[docling]" in message
    assert "CCORE_DOCUMENT_ENGINE=simple" in message


@pytest.mark.asyncio
async def test_extract_explicit_docling_missing_raises():
    """An explicitly named engine is honored or it raises -- never substituted."""
    cfg = ContentCoreConfig(document_engine="docling")
    with _docling_missing(), patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ), patch(
        "content_core.extraction.extract_pdf_file", new_callable=AsyncMock
    ) as mock_pdf:
        with pytest.raises(ConfigurationError) as exc_info:
            await extract_content(file_path="/tmp/test.pdf", config=cfg)
        mock_pdf.assert_not_awaited()
    assert "pip install content-core[docling]" in str(exc_info.value)
    assert "CCORE_DOCUMENT_ENGINE=simple" in str(exc_info.value)


def test_route_for_mime_auto_docling_missing_falls_back():
    """`auto` is a preference: it degrades to the standard processors silently."""
    cfg = ContentCoreConfig(document_engine="auto")
    with _docling_missing():
        assert _route_for_mime("application/pdf", cfg) == "pdf"


@pytest.mark.asyncio
async def test_extract_auto_docling_missing_uses_standard_processor():
    cfg = ContentCoreConfig(document_engine="auto")
    expected = _make_output(identified_type="application/pdf")
    with _docling_missing(), patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ), patch(
        "content_core.extraction.extract_pdf_file",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_pdf:
        result = await extract_content(file_path="/tmp/test.pdf", config=cfg)
    mock_pdf.assert_awaited_once()
    assert result is expected


def test_route_for_mime_explicit_docling_installed_still_routes():
    """Docling-available paths are unchanged."""
    cfg = ContentCoreConfig(document_engine="docling")
    with _docling_installed(AsyncMock()):
        assert _route_for_mime("application/pdf", cfg) == "docling"


def test_route_for_mime_auto_docling_installed_still_routes():
    cfg = ContentCoreConfig(document_engine="auto")
    with _docling_installed(AsyncMock()), patch(
        "content_core.extraction.DOCLING_SUPPORTED", {"application/pdf"}
    ):
        assert _route_for_mime("application/pdf", cfg) == "docling"


@pytest.mark.asyncio
async def test_check_file_support_explicit_docling_missing_is_a_verdict():
    """Pre-flight reports the unhonorable engine as a verdict, it does not raise."""
    cfg = ContentCoreConfig(document_engine="docling")
    with _docling_missing(), patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ):
        result = await check_file_support("/tmp/test.pdf", config=cfg)
    assert result.supported is False
    assert result.processor is None
    assert result.identified_type == "application/pdf"
    assert result.document_engine == "docling"
    assert "pip install content-core[docling]" in result.reason
    assert "CCORE_DOCUMENT_ENGINE=simple" in result.reason


@pytest.mark.asyncio
async def test_check_file_support_reason_matches_extraction_error():
    """The pre-flight reason is the very message extraction would raise with."""
    cfg = ContentCoreConfig(document_engine="docling")
    with _docling_missing(), patch(
        "content_core.content.identification.get_file_type",
        new_callable=AsyncMock,
        return_value="application/pdf",
    ):
        verdict = await check_file_support("/tmp/test.pdf", config=cfg)
        with pytest.raises(ConfigurationError) as exc_info:
            await extract_content(file_path="/tmp/test.pdf", config=cfg)
    assert verdict.reason == str(exc_info.value)


def test_configuration_error_is_exported_from_package():
    import content_core

    assert content_core.ConfigurationError is ConfigurationError
    assert "ConfigurationError" in content_core.__all__
