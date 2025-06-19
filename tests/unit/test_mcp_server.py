"""Unit tests for MCP server."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from content_core.mcp.server import _extract_content_impl as extract_content


class TestMCPServer:
    """Test cases for MCP server functionality."""

    @pytest.mark.asyncio 
    async def test_extract_content_no_params(self):
        """Test extract_content with no parameters."""
        result = await extract_content()
        assert result["success"] is False
        assert "Exactly one of 'url' or 'file_path' must be provided" in result["error"]
        assert result["source_type"] is None
        assert result["content"] is None

    @pytest.mark.asyncio
    async def test_extract_content_both_params(self):
        """Test extract_content with both parameters."""
        result = await extract_content(url="https://example.com", file_path="test.txt")
        assert result["success"] is False
        assert "Exactly one of 'url' or 'file_path' must be provided" in result["error"]
        assert result["source_type"] is None
        assert result["content"] is None

    @pytest.mark.asyncio
    async def test_extract_content_nonexistent_file(self):
        """Test extract_content with non-existent file."""
        result = await extract_content(file_path="nonexistent_file.txt")
        assert result["success"] is False
        assert "File not found" in result["error"]
        assert result["source_type"] == "file"
        assert result["content"] is None

    @pytest.mark.asyncio
    async def test_extract_content_file_success(self):
        """Test successful file extraction."""
        # Create a temporary test file
        test_file = Path("test_mcp_file.txt")
        test_content = "This is test content for MCP server."
        test_file.write_text(test_content)
        
        try:
            # Mock the content_core.extract_content function
            mock_result = MagicMock()
            mock_result.content = test_content
            mock_result.title = "test_mcp_file.txt"
            mock_result.file_path = str(test_file.resolve())
            mock_result.source_type = "file"
            mock_result.identified_type = "text/plain"
            mock_result.identified_provider = ""
            mock_result.metadata = {}
            
            with patch('content_core.mcp.server.cc.extract_content', return_value=mock_result):
                result = await extract_content(file_path=str(test_file))
                
                assert result["success"] is True
                assert result["error"] is None
                assert result["source_type"] == "file"
                assert result["content"] == test_content
                assert result["metadata"]["identified_type"] == "text/plain"
                assert result["metadata"]["file_extension"] == ".txt"
                assert result["metadata"]["content_length"] == len(test_content)
                assert "extraction_timestamp" in result["metadata"]
                assert "extraction_time_seconds" in result["metadata"]
                
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()

    @pytest.mark.asyncio
    async def test_extract_content_url_success(self):
        """Test successful URL extraction."""
        test_url = "https://example.com"
        test_content = "This is example content from a webpage."
        test_title = "Example Page"
        
        # Mock the content_core.extract_content function
        mock_result = MagicMock()
        mock_result.content = test_content
        mock_result.title = test_title
        mock_result.url = test_url
        mock_result.source_type = "url"
        mock_result.identified_type = "text/html"
        mock_result.identified_provider = ""
        mock_result.metadata = {"some_key": "some_value"}
        
        with patch('content_core.mcp.server.cc.extract_content', return_value=mock_result):
            result = await extract_content(url=test_url)
            
            assert result["success"] is True
            assert result["error"] is None
            assert result["source_type"] == "url"
            assert result["content"] == test_content
            assert result["metadata"]["identified_type"] == "text/html"
            assert result["metadata"]["title"] == test_title
            assert result["metadata"]["final_url"] == test_url
            assert result["metadata"]["content_length"] == len(test_content)
            assert result["metadata"]["some_key"] == "some_value"
            assert "extraction_timestamp" in result["metadata"]
            assert "extraction_time_seconds" in result["metadata"]

    @pytest.mark.asyncio
    async def test_extract_content_exception_handling(self):
        """Test extract_content exception handling."""
        test_url = "https://example.com"
        
        # Mock content_core.extract_content to raise an exception
        with patch('content_core.mcp.server.cc.extract_content', side_effect=Exception("Test error")):
            result = await extract_content(url=test_url)
            
            assert result["success"] is False
            assert result["error"] == "Test error"
            assert result["source_type"] == "url"
            assert result["source"] == test_url
            assert result["content"] is None
            assert result["metadata"]["error_type"] == "Exception"
            assert "extraction_timestamp" in result["metadata"]