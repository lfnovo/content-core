"""Unit tests for API schemas."""

import pytest
from pydantic import ValidationError

from content_core.api.schemas import (
    EngineInfo,
    EnginesResponse,
    ErrorResponse,
    ExtractionRequest,
    ExtractionResponse,
    HealthResponse,
    ReadyResponse,
)


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_valid_response(self):
        """Test creating a valid health response."""
        response = HealthResponse(status="healthy", version="1.0.0")
        assert response.status == "healthy"
        assert response.version == "1.0.0"

    def test_serialization(self):
        """Test JSON serialization."""
        response = HealthResponse(status="healthy", version="2.0.0")
        data = response.model_dump()
        assert data == {"status": "healthy", "version": "2.0.0"}


class TestReadyResponse:
    """Tests for ReadyResponse schema."""

    def test_valid_response(self):
        """Test creating a valid ready response."""
        response = ReadyResponse(
            status="ready",
            checks={"processors": True, "database": True},
        )
        assert response.status == "ready"
        assert response.checks["processors"] is True

    def test_not_ready_response(self):
        """Test creating a not ready response."""
        response = ReadyResponse(
            status="not_ready",
            checks={"processors": False},
        )
        assert response.status == "not_ready"


class TestEngineInfo:
    """Tests for EngineInfo schema."""

    def test_valid_engine_info(self):
        """Test creating valid engine info."""
        info = EngineInfo(
            name="docling",
            available=True,
            mime_types=["application/pdf", "image/*"],
            extensions=[".pdf", ".png"],
            priority=60,
            category="documents",
            requires=["docling"],
        )
        assert info.name == "docling"
        assert info.available is True
        assert len(info.mime_types) == 2
        assert info.priority == 60

    def test_default_requires(self):
        """Test default empty requires list."""
        info = EngineInfo(
            name="text",
            available=True,
            mime_types=["text/plain"],
            extensions=[".txt"],
            priority=50,
            category="documents",
        )
        assert info.requires == []


class TestEnginesResponse:
    """Tests for EnginesResponse schema."""

    def test_valid_response(self):
        """Test creating valid engines response."""
        response = EnginesResponse(
            engines=[
                EngineInfo(
                    name="docling",
                    available=True,
                    mime_types=["application/pdf"],
                    extensions=[".pdf"],
                    priority=60,
                    category="documents",
                ),
            ]
        )
        assert len(response.engines) == 1
        assert response.engines[0].name == "docling"


class TestExtractionRequest:
    """Tests for ExtractionRequest schema."""

    def test_url_request(self):
        """Test creating request with URL."""
        request = ExtractionRequest(url="https://example.com/doc.pdf")
        assert request.url == "https://example.com/doc.pdf"
        assert request.content is None
        assert request.engine is None
        assert request.timeout == 300

    def test_content_request(self):
        """Test creating request with content."""
        request = ExtractionRequest(content="Hello world")
        assert request.content == "Hello world"
        assert request.url is None

    def test_with_options(self):
        """Test creating request with options."""
        request = ExtractionRequest(
            url="https://example.com",
            engine="jina",
            timeout=60,
            options={"ocr": True},
        )
        assert request.engine == "jina"
        assert request.timeout == 60
        assert request.options == {"ocr": True}

    def test_empty_string_becomes_none(self):
        """Test that empty strings are converted to None."""
        request = ExtractionRequest(url="   ", content="")
        assert request.url is None
        assert request.content is None

    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeouts
        ExtractionRequest(url="https://example.com", timeout=1)
        ExtractionRequest(url="https://example.com", timeout=3600)

        # Invalid timeouts
        with pytest.raises(ValidationError):
            ExtractionRequest(url="https://example.com", timeout=0)
        with pytest.raises(ValidationError):
            ExtractionRequest(url="https://example.com", timeout=3601)


class TestExtractionResponse:
    """Tests for ExtractionResponse schema."""

    def test_valid_response(self):
        """Test creating valid extraction response."""
        response = ExtractionResponse(
            content="# Hello\n\nThis is content.",
            source_type="url",
            mime_type="text/html",
            engine_used="jina",
            metadata={"title": "Example"},
            warnings=["Some warning"],
        )
        assert response.content == "# Hello\n\nThis is content."
        assert response.source_type == "url"
        assert response.mime_type == "text/html"
        assert response.engine_used == "jina"
        assert response.metadata["title"] == "Example"
        assert len(response.warnings) == 1

    def test_default_values(self):
        """Test default values."""
        response = ExtractionResponse(
            content="Hello",
            source_type="content",
            engine_used="text",
        )
        assert response.mime_type is None
        assert response.metadata == {}
        assert response.warnings == []


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_simple_error(self):
        """Test creating simple error response."""
        response = ErrorResponse(error="Something went wrong")
        assert response.error == "Something went wrong"
        assert response.detail is None
        assert response.error_type is None

    def test_detailed_error(self):
        """Test creating detailed error response."""
        response = ErrorResponse(
            error="Extraction failed",
            detail="The URL is not reachable",
            error_type="NetworkError",
        )
        assert response.error == "Extraction failed"
        assert response.detail == "The URL is not reachable"
        assert response.error_type == "NetworkError"
