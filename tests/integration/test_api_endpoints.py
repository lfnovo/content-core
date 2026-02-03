"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from content_core.api import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app(include_ui=False)
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, client):
        """Test /api/v1/health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_ready_endpoint(self, client):
        """Test /api/v1/ready endpoint."""
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]
        assert "checks" in data
        assert isinstance(data["checks"], dict)


class TestEnginesEndpoint:
    """Tests for engines listing endpoint."""

    def test_list_engines(self, client):
        """Test /api/v1/engines endpoint."""
        response = client.get("/api/v1/engines")
        assert response.status_code == 200
        data = response.json()
        assert "engines" in data
        assert isinstance(data["engines"], list)

        # If there are engines, check structure
        if len(data["engines"]) > 0:
            engine = data["engines"][0]
            assert "name" in engine
            assert "available" in engine
            assert "mime_types" in engine
            assert "extensions" in engine
            assert "priority" in engine
            assert "category" in engine

    def test_list_engines_include_unavailable(self, client):
        """Test /api/v1/engines?include_unavailable=true endpoint."""
        response = client.get("/api/v1/engines?include_unavailable=true")
        assert response.status_code == 200
        data = response.json()
        assert "engines" in data
        assert isinstance(data["engines"], list)

        # Should return more engines than the default (available only)
        response_available = client.get("/api/v1/engines")
        available_count = len(response_available.json()["engines"])
        all_count = len(data["engines"])
        # All engines should include at least the available ones
        assert all_count >= available_count

        # Unavailable engines should have a reason
        for engine in data["engines"]:
            assert "reason" in engine
            if not engine["available"]:
                # Unavailable engines should have a reason explaining why
                assert engine["reason"] is not None


class TestExtractEndpoint:
    """Tests for content extraction endpoints."""

    def test_extract_missing_source(self, client):
        """Test extraction with no source provided."""
        response = client.post(
            "/api/v1/extract",
            json={},
        )
        assert response.status_code == 400
        assert "url" in response.json()["detail"].lower() or "content" in response.json()["detail"].lower()

    def test_extract_multiple_sources(self, client):
        """Test extraction with multiple sources provided."""
        response = client.post(
            "/api/v1/extract",
            json={
                "url": "https://example.com",
                "content": "some content",
            },
        )
        assert response.status_code == 400
        assert "only one" in response.json()["detail"].lower()

    def test_extract_text_content(self, client):
        """Test extraction from text content."""
        response = client.post(
            "/api/v1/extract",
            json={
                "content": "Hello, this is a test document.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "source_type" in data
        assert "engine_used" in data

    def test_extract_with_timeout(self, client):
        """Test extraction with custom timeout."""
        response = client.post(
            "/api/v1/extract",
            json={
                "content": "Test content",
                "timeout": 60,
            },
        )
        assert response.status_code == 200

    def test_extract_invalid_timeout(self, client):
        """Test extraction with invalid timeout."""
        response = client.post(
            "/api/v1/extract",
            json={
                "content": "Test content",
                "timeout": 0,
            },
        )
        assert response.status_code == 422  # Validation error


class TestExtractFileEndpoint:
    """Tests for file upload extraction endpoint."""

    def test_extract_file_no_file(self, client):
        """Test file extraction without file."""
        response = client.post("/api/v1/extract/file")
        assert response.status_code == 422  # Missing required file

    def test_extract_text_file(self, client):
        """Test extraction from a text file."""
        file_content = b"This is a test text file content."
        response = client.post(
            "/api/v1/extract/file",
            files={"file": ("test.txt", file_content, "text/plain")},
        )
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert "test text file" in data["content"].lower()


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""

    def test_openapi_json(self, client):
        """Test OpenAPI JSON endpoint."""
        response = client.get("/api/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "/api/v1/health" in data["paths"]

    def test_docs_endpoint(self, client):
        """Test Swagger UI endpoint."""
        response = client.get("/api/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_redoc_endpoint(self, client):
        """Test ReDoc endpoint."""
        response = client.get("/api/redoc")
        assert response.status_code == 200
