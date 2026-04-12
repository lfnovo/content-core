"""Unit tests for content_core.processors.document.pdf."""

from unittest.mock import AsyncMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.document.pdf import clean_pdf_text, extract_pdf_file


class TestCleanPdfText:
    def test_ligature_fi(self):
        assert "fi" in clean_pdf_text("ﬁnd")

    def test_ligature_fl(self):
        assert "fl" in clean_pdf_text("ﬂow")

    def test_excessive_whitespace_collapsed(self):
        result = clean_pdf_text("hello     world")
        assert "hello world" in result

    def test_hyphenation_at_line_break(self):
        result = clean_pdf_text("word-\nbreak")
        assert "wordbreak" in result

    def test_empty_string_returns_as_is(self):
        assert clean_pdf_text("") == ""

    def test_none_returns_none(self):
        assert clean_pdf_text(None) is None

    def test_multiple_newlines_collapsed(self):
        result = clean_pdf_text("para1\n\n\n\n\npara2")
        assert "\n\n\n" not in result
        assert "para1" in result
        assert "para2" in result


class TestExtractPdfFile:
    @pytest.fixture
    def config(self):
        return ContentCoreConfig()

    async def test_successful_extraction(self, config):
        with patch(
            "content_core.processors.document.pdf._extract_text_from_pdf",
            new_callable=AsyncMock,
            return_value="Extracted PDF content",
        ):
            result = await extract_pdf_file("/fake/document.pdf", config)
            assert result.content == "Extracted PDF content"
            assert result.source_type == "file"
            assert result.identified_type == "application/pdf"

    async def test_file_not_found_raises(self, config):
        with patch(
            "content_core.processors.document.pdf._extract_text_from_pdf",
            new_callable=AsyncMock,
            side_effect=FileNotFoundError("not found"),
        ):
            with pytest.raises(FileNotFoundError):
                await extract_pdf_file("/no/such/file.pdf", config)
