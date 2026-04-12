"""Unit tests for content_core.processors.document.docling."""

from unittest.mock import MagicMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.document.docling import extract_docling


@pytest.fixture
def mock_document():
    doc = MagicMock()
    doc.export_to_markdown.return_value = "# Markdown Content\n\nSome text"
    doc.export_to_html.return_value = "<h1>HTML Content</h1><p>Some text</p>"
    doc.export_to_json.return_value = '{"content": "JSON Content"}'
    return doc


@pytest.fixture
def mock_converter(mock_document):
    converter = MagicMock()
    result = MagicMock()
    result.document = mock_document
    converter.convert.return_value = result
    return converter


class TestExtractDocling:
    async def test_markdown_output(self, mock_converter):
        config = ContentCoreConfig(docling_output_format="markdown")
        with patch(
            "content_core.processors.document.docling.DocumentConverter",
            return_value=mock_converter,
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            assert result.content == "# Markdown Content\n\nSome text"
            assert result.source_type == "file"
            assert result.metadata["docling_format"] == "markdown"

    async def test_html_output(self, mock_converter):
        config = ContentCoreConfig(docling_output_format="html")
        with patch(
            "content_core.processors.document.docling.DocumentConverter",
            return_value=mock_converter,
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            assert "<h1>" in result.content
            assert result.metadata["docling_format"] == "html"

    async def test_json_output(self, mock_converter):
        config = ContentCoreConfig(docling_output_format="json")
        with patch(
            "content_core.processors.document.docling.DocumentConverter",
            return_value=mock_converter,
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            assert "JSON Content" in result.content
            assert result.metadata["docling_format"] == "json"

    async def test_default_format_is_markdown(self, mock_converter):
        config = ContentCoreConfig()  # defaults to "markdown"
        with patch(
            "content_core.processors.document.docling.DocumentConverter",
            return_value=mock_converter,
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            mock_converter.convert.assert_called_once_with("/fake/doc.pdf")
            assert "Markdown Content" in result.content

    async def test_returns_extraction_output(self, mock_converter):
        config = ContentCoreConfig()
        with patch(
            "content_core.processors.document.docling.DocumentConverter",
            return_value=mock_converter,
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            from content_core.common.state import ExtractionOutput

            assert isinstance(result, ExtractionOutput)

    async def test_empty_source_raises_value_error(self, mock_converter):
        config = ContentCoreConfig()
        with patch(
            "content_core.processors.document.docling.DocumentConverter",
            return_value=mock_converter,
        ):
            with pytest.raises(ValueError, match="No input provided"):
                await extract_docling("", config)

    async def test_ocr_enabled_by_default(self):
        """Default config has OCR enabled."""
        config = ContentCoreConfig()
        assert config.docling_ocr is True

    async def test_formulas_disabled_by_default(self):
        """Default config has formulas disabled."""
        config = ContentCoreConfig()
        assert config.docling_formulas is False

    async def test_vision_disabled_by_default(self):
        """Default config has vision disabled."""
        config = ContentCoreConfig()
        assert config.docling_vision is False

    async def test_formulas_flag_passed_to_pipeline(self):
        """docling_formulas=True should pass do_formula_enrichment=True."""
        config = ContentCoreConfig(docling_formulas=True)
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "content"
        mock_pipeline_options_cls = MagicMock()
        mock_pdf_format_option_cls = MagicMock()
        mock_input_format = MagicMock()
        with patch(
            "content_core.processors.document.docling.DocumentConverter"
        ) as MockConverter, patch(
            "content_core.processors.document.docling.DOCLING_AVAILABLE", True
        ), patch(
            "content_core.processors.document.docling.PdfPipelineOptions", mock_pipeline_options_cls
        ), patch(
            "content_core.processors.document.docling.PdfFormatOption", mock_pdf_format_option_cls
        ), patch(
            "content_core.processors.document.docling.InputFormat", mock_input_format
        ):
            MockConverter.return_value.convert.return_value = mock_result
            await extract_docling("/fake/doc.pdf", config)
            # Verify DocumentConverter was called with format_options
            call_kwargs = MockConverter.call_args[1]
            assert "format_options" in call_kwargs

    async def test_vision_flag_passed_to_pipeline(self):
        """docling_vision=True should enable picture description and chart extraction."""
        config = ContentCoreConfig(docling_vision=True)
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "content"
        mock_pipeline_options_cls = MagicMock()
        mock_pdf_format_option_cls = MagicMock()
        mock_input_format = MagicMock()
        with patch(
            "content_core.processors.document.docling.DocumentConverter"
        ) as MockConverter, patch(
            "content_core.processors.document.docling.DOCLING_AVAILABLE", True
        ), patch(
            "content_core.processors.document.docling.PdfPipelineOptions", mock_pipeline_options_cls
        ), patch(
            "content_core.processors.document.docling.PdfFormatOption", mock_pdf_format_option_cls
        ), patch(
            "content_core.processors.document.docling.InputFormat", mock_input_format
        ):
            MockConverter.return_value.convert.return_value = mock_result
            await extract_docling("/fake/doc.pdf", config)
            call_kwargs = MockConverter.call_args[1]
            assert "format_options" in call_kwargs
