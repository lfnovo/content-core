"""Unit tests for content_core.processors.document (office extraction)."""

from unittest.mock import AsyncMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.document import extract_office


@pytest.fixture
def config():
    return ContentCoreConfig()


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class TestExtractOfficeRouting:
    async def test_docx_calls_docx_extractor(self, config):
        with patch(
            "content_core.processors.document.extract_docx_content_detailed",
            new_callable=AsyncMock,
            return_value="# Heading\n\nDocx content",
        ) as mock_docx:
            result = await extract_office("/fake/doc.docx", DOCX_MIME, config)
            mock_docx.assert_called_once_with("/fake/doc.docx")
            assert result.content == "# Heading\n\nDocx content"
            assert result.source_type == "file"
            assert result.identified_type == DOCX_MIME

    async def test_pptx_calls_pptx_extractor(self, config):
        with patch(
            "content_core.processors.document.extract_pptx_content",
            new_callable=AsyncMock,
            return_value="# Slide 1\n\n## Title\n\nSlide content",
        ) as mock_pptx:
            result = await extract_office("/fake/pres.pptx", PPTX_MIME, config)
            mock_pptx.assert_called_once_with("/fake/pres.pptx")
            assert "Slide content" in result.content
            assert result.identified_type == PPTX_MIME

    async def test_xlsx_calls_xlsx_extractor(self, config):
        with patch(
            "content_core.processors.document.extract_xlsx_content",
            new_callable=AsyncMock,
            return_value="| Col1 | Col2 |\n| --- | --- |\n| A | B |",
        ) as mock_xlsx:
            result = await extract_office("/fake/data.xlsx", XLSX_MIME, config)
            mock_xlsx.assert_called_once_with("/fake/data.xlsx")
            assert "Col1" in result.content
            assert result.identified_type == XLSX_MIME

    async def test_unknown_mime_raises_value_error(self, config):
        with pytest.raises(ValueError, match="Unsupported Office MIME type"):
            await extract_office("/fake/file.odt", "application/odt", config)

    async def test_docx_returns_extraction_output(self, config):
        with patch(
            "content_core.processors.document.extract_docx_content_detailed",
            new_callable=AsyncMock,
            return_value="# Report\n\nContent here",
        ):
            result = await extract_office("/fake/report.docx", DOCX_MIME, config)
            assert result.source_type == "file"
            assert result.identified_type == DOCX_MIME
            assert "Report" in result.content

    async def test_pptx_returns_slide_content(self, config):
        slide_content = "# Slide 1\n\n## Intro\n\nWelcome to the presentation"
        with patch(
            "content_core.processors.document.extract_pptx_content",
            new_callable=AsyncMock,
            return_value=slide_content,
        ):
            result = await extract_office("/fake/deck.pptx", PPTX_MIME, config)
            assert "Welcome to the presentation" in result.content

    async def test_xlsx_returns_table_content(self, config):
        table_content = "| Name | Age |\n| --- | --- |\n| Alice | 30 |"
        with patch(
            "content_core.processors.document.extract_xlsx_content",
            new_callable=AsyncMock,
            return_value=table_content,
        ):
            result = await extract_office("/fake/sheet.xlsx", XLSX_MIME, config)
            assert "Alice" in result.content
            assert "30" in result.content

    async def test_none_content_returns_empty_string(self, config):
        with patch(
            "content_core.processors.document.extract_docx_content_detailed",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await extract_office("/fake/empty.docx", DOCX_MIME, config)
            assert result.content == ""
