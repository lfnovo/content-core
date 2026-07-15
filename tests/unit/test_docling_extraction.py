"""Unit tests for content_core.processors.document.docling."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from content_core.config import ContentCoreConfig
from content_core.common.exceptions import DocumentExtractionError
from content_core.processors.document.docling import (
    _docling_file_endpoint,
    _docling_form_fields,
    _docling_headers,
    _normalize_docling_api_url,
    extract_docling,
)


class FakeResponse:
    def __init__(self, *, status=200, body=None):
        self.status = status
        self._body = body if body is not None else "{}"

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self):
        return self._body


class FakeSession:
    def __init__(self, *, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.post_calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        self.post_calls.append((args, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.response


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
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                MagicMock(),
                MagicMock(),
                MagicMock(return_value=mock_converter),
                MagicMock(),
            ),
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            assert result.content == "# Markdown Content\n\nSome text"
            assert result.source_type == "file"
            assert result.metadata["docling_format"] == "markdown"

    async def test_html_output(self, mock_converter):
        config = ContentCoreConfig(docling_output_format="html")
        with patch(
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                MagicMock(),
                MagicMock(),
                MagicMock(return_value=mock_converter),
                MagicMock(),
            ),
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            assert "<h1>" in result.content
            assert result.metadata["docling_format"] == "html"

    async def test_json_output(self, mock_converter):
        config = ContentCoreConfig(docling_output_format="json")
        with patch(
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                MagicMock(),
                MagicMock(),
                MagicMock(return_value=mock_converter),
                MagicMock(),
            ),
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            assert "JSON Content" in result.content
            assert result.metadata["docling_format"] == "json"

    async def test_default_format_is_markdown(self, mock_converter):
        config = ContentCoreConfig()  # defaults to "markdown"
        with patch(
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                MagicMock(),
                MagicMock(),
                MagicMock(return_value=mock_converter),
                MagicMock(),
            ),
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            mock_converter.convert.assert_called_once_with("/fake/doc.pdf")
            assert "Markdown Content" in result.content

    async def test_returns_extraction_output(self, mock_converter):
        config = ContentCoreConfig()
        with patch(
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                MagicMock(),
                MagicMock(),
                MagicMock(return_value=mock_converter),
                MagicMock(),
            ),
        ):
            result = await extract_docling("/fake/doc.pdf", config)
            from content_core.common.state import ExtractionOutput

            assert isinstance(result, ExtractionOutput)

    async def test_empty_source_raises_value_error(self, mock_converter):
        config = ContentCoreConfig()
        with patch(
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                MagicMock(),
                MagicMock(),
                MagicMock(return_value=mock_converter),
                MagicMock(),
            ),
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
        mock_document_converter_cls = MagicMock()
        with patch(
            "content_core.processors.document.docling.DOCLING_AVAILABLE", True
        ), patch(
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                mock_input_format,
                mock_pipeline_options_cls,
                mock_document_converter_cls,
                mock_pdf_format_option_cls,
            ),
        ):
            mock_document_converter_cls.return_value.convert.return_value = mock_result
            await extract_docling("/fake/doc.pdf", config)
            # Verify DocumentConverter was called with format_options
            call_kwargs = mock_document_converter_cls.call_args[1]
            assert "format_options" in call_kwargs
            # Verify pipeline option values match config
            pipeline_call_kwargs = mock_pipeline_options_cls.call_args[1]
            assert pipeline_call_kwargs["do_ocr"] == config.docling_ocr
            assert pipeline_call_kwargs["do_formula_enrichment"] is True
            assert (
                pipeline_call_kwargs["do_picture_description"] == config.docling_vision
            )
            assert pipeline_call_kwargs["do_chart_extraction"] == config.docling_vision

    async def test_vision_flag_passed_to_pipeline(self):
        """docling_vision=True should enable picture description and chart extraction."""
        config = ContentCoreConfig(docling_vision=True)
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = "content"
        mock_pipeline_options_cls = MagicMock()
        mock_pdf_format_option_cls = MagicMock()
        mock_input_format = MagicMock()
        mock_document_converter_cls = MagicMock()
        with patch(
            "content_core.processors.document.docling.DOCLING_AVAILABLE", True
        ), patch(
            "content_core.processors.document.docling._load_docling_classes",
            return_value=(
                mock_input_format,
                mock_pipeline_options_cls,
                mock_document_converter_cls,
                mock_pdf_format_option_cls,
            ),
        ):
            mock_document_converter_cls.return_value.convert.return_value = mock_result
            await extract_docling("/fake/doc.pdf", config)
            call_kwargs = mock_document_converter_cls.call_args[1]
            assert "format_options" in call_kwargs
            # Verify pipeline option values match config
            pipeline_call_kwargs = mock_pipeline_options_cls.call_args[1]
            assert pipeline_call_kwargs["do_ocr"] == config.docling_ocr
            assert (
                pipeline_call_kwargs["do_formula_enrichment"] == config.docling_formulas
            )
            assert pipeline_call_kwargs["do_picture_description"] is True
            assert pipeline_call_kwargs["do_chart_extraction"] is True

    async def test_remote_precedence_over_local(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(docling_api_url="https://docling.example")

        remote_result = MagicMock()
        with patch(
            "content_core.processors.document.docling._extract_docling_remote",
            return_value=remote_result,
        ) as mock_remote, patch(
            "content_core.processors.document.docling._extract_docling_local",
        ) as mock_local:
            result = await extract_docling(str(source), config)

        assert result is remote_result
        mock_remote.assert_awaited_once_with(str(source), config)
        mock_local.assert_not_called()

    async def test_local_behavior_when_remote_url_absent(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig()

        local_result = MagicMock()
        with patch(
            "content_core.processors.document.docling._extract_docling_remote",
        ) as mock_remote, patch(
            "content_core.processors.document.docling._extract_docling_local",
            return_value=local_result,
        ) as mock_local:
            result = await extract_docling(str(source), config)

        assert result is local_result
        mock_local.assert_awaited_once_with(str(source), config)
        mock_remote.assert_not_called()


class TestDoclingServeHelpers:
    def test_normalize_docling_api_url(self):
        assert (
            _normalize_docling_api_url("https://docling.example")
            == "https://docling.example/v1"
        )
        assert (
            _normalize_docling_api_url("https://docling.example/")
            == "https://docling.example/v1"
        )
        assert (
            _normalize_docling_api_url("https://docling.example/v1")
            == "https://docling.example/v1"
        )
        assert (
            _normalize_docling_api_url("https://docling.example/v1/")
            == "https://docling.example/v1"
        )
        assert (
            _normalize_docling_api_url("https://docling.example/v1/convert/file")
            == "https://docling.example/v1"
        )

    def test_docling_file_endpoint(self):
        assert (
            _docling_file_endpoint("https://docling.example")
            == "https://docling.example/v1/convert/file"
        )
        assert (
            _docling_file_endpoint("https://docling.example/v1")
            == "https://docling.example/v1/convert/file"
        )

    def test_authentication_header(self):
        config = ContentCoreConfig(docling_api_key="secret-token")
        headers = _docling_headers(config)
        assert headers["accept"] == "application/json"
        assert headers["X-Api-Key"] == "secret-token"

    def test_ocr_option_mapping(self):
        config = ContentCoreConfig(
            docling_ocr=False,
            docling_formulas=True,
            docling_vision=True,
        )
        assert _docling_form_fields(config) == [
            ("to_formats", "md"),
            ("do_ocr", "false"),
            ("abort_on_error", "true"),
            ("do_formula_enrichment", "true"),
            ("do_picture_description", "true"),
            ("do_chart_extraction", "true"),
        ]


class TestRemoteDoclingServe:
    async def test_remote_success(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(
            docling_api_url="https://docling.example", docling_timeout=42
        )
        payload = {"document": {"md_content": "# Converted"}}
        session = FakeSession(response=FakeResponse(body=json.dumps(payload)))

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await extract_docling(str(source), config)

        assert result.content == "# Converted"
        assert result.metadata["docling_backend"] == "remote"
        args, kwargs = session.post_calls[0]
        assert args[0] == "https://docling.example/v1/convert/file"
        assert kwargs["headers"]["accept"] == "application/json"
        assert kwargs["timeout"].total == 42

    async def test_remote_success_with_authentication_header(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(
            docling_api_url="https://docling.example",
            docling_api_key="secret-token",
        )
        payload = {"document": {"md_content": "# Converted"}}
        session = FakeSession(response=FakeResponse(body=json.dumps(payload)))

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            await extract_docling(str(source), config)

        _, kwargs = session.post_calls[0]
        assert kwargs["headers"]["X-Api-Key"] == "secret-token"

    async def test_remote_timeout(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(
            docling_api_url="https://docling.example", docling_timeout=7
        )
        session = FakeSession(exc=asyncio.TimeoutError())

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            with pytest.raises(DocumentExtractionError, match="timed out"):
                await extract_docling(str(source), config)

    async def test_remote_connection_failure(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(docling_api_url="https://docling.example")
        session = FakeSession(exc=aiohttp.ClientConnectionError("dns failure"))

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            with pytest.raises(DocumentExtractionError, match="request failed"):
                await extract_docling(str(source), config)

    async def test_remote_server_error(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(docling_api_url="https://docling.example")
        session = FakeSession(
            response=FakeResponse(
                status=502, body=json.dumps({"detail": "bad gateway"})
            )
        )

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            with pytest.raises(DocumentExtractionError, match="HTTP 502: bad gateway"):
                await extract_docling(str(source), config)

    async def test_remote_malformed_response(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(docling_api_url="https://docling.example")
        session = FakeSession(response=FakeResponse(body="not json"))

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            with pytest.raises(DocumentExtractionError, match="invalid JSON"):
                await extract_docling(str(source), config)

    async def test_remote_empty_content(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(docling_api_url="https://docling.example")
        session = FakeSession(
            response=FakeResponse(body=json.dumps({"document": {"md_content": "   "}}))
        )

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            with pytest.raises(DocumentExtractionError, match="no markdown content"):
                await extract_docling(str(source), config)

    async def test_remote_conversion_failure_reported(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(docling_api_url="https://docling.example")
        payload = {"document": {"failure": "conversion failed"}}
        session = FakeSession(response=FakeResponse(body=json.dumps(payload)))

        with patch(
            "content_core.processors.document.docling.aiohttp.ClientSession",
            return_value=session,
        ):
            with pytest.raises(DocumentExtractionError, match="conversion failed"):
                await extract_docling(str(source), config)

    async def test_remote_non_markdown_output_rejected(self, tmp_path):
        source = tmp_path / "report.pdf"
        source.write_bytes(b"pdf")
        config = ContentCoreConfig(
            docling_api_url="https://docling.example",
            docling_output_format="html",
        )

        with pytest.raises(
            DocumentExtractionError,
            match="supports only docling_output_format='markdown'",
        ):
            await extract_docling(str(source), config)
