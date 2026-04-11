"""Tests for the MCP server v2."""
from unittest.mock import AsyncMock, patch

import pytest

from content_core.mcp.server import extract_content as _extract_tool
from content_core.mcp.server import summarize_content as _summarize_tool

# Access the underlying async functions from the FastMCP FunctionTool wrappers
extract_content_fn = _extract_tool.fn
summarize_content_fn = _summarize_tool.fn


class TestExtractContent:
    @pytest.mark.asyncio
    async def test_extract_url(self):
        with patch(
            "content_core.extraction.extract_content", new_callable=AsyncMock
        ) as mock:
            from content_core.models_v2 import ExtractionOutput

            mock.return_value = ExtractionOutput(content="extracted text")
            result = await extract_content_fn(url="https://example.com")
            assert result == "extracted text"

    @pytest.mark.asyncio
    async def test_extract_file(self):
        with patch(
            "content_core.extraction.extract_content", new_callable=AsyncMock
        ) as mock:
            from content_core.models_v2 import ExtractionOutput

            mock.return_value = ExtractionOutput(content="file content")
            result = await extract_content_fn(file_path="/tmp/test.pdf")
            assert result == "file content"

    @pytest.mark.asyncio
    async def test_no_params_returns_error(self):
        result = await extract_content_fn()
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_both_params_returns_error(self):
        result = await extract_content_fn(
            url="https://example.com", file_path="/tmp/test.pdf"
        )
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_engine_param_forwarded(self):
        with patch(
            "content_core.extraction.extract_content", new_callable=AsyncMock
        ) as mock_extract, patch(
            "content_core.config.ContentCoreConfig"
        ) as mock_config:
            from content_core.models_v2 import ExtractionOutput

            mock_extract.return_value = ExtractionOutput(content="text")
            await extract_content_fn(url="https://example.com", engine="firecrawl")
            mock_config.assert_called_once_with(url_engine="firecrawl")

    @pytest.mark.asyncio
    async def test_extract_error(self):
        with patch(
            "content_core.extraction.extract_content", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = Exception("Network error")
            result = await extract_content_fn(url="https://example.com")
            assert "Error" in result
            assert "Network error" in result


class TestSummarizeContent:
    @pytest.mark.asyncio
    async def test_summarize(self):
        with patch(
            "content_core.content.summary.summarize", new_callable=AsyncMock
        ) as mock:
            mock.return_value = "summary text"
            result = await summarize_content_fn(
                content="long text", context="bullet points"
            )
            assert result == "summary text"
            mock.assert_called_once_with("long text", "bullet points")

    @pytest.mark.asyncio
    async def test_summarize_error(self):
        with patch(
            "content_core.content.summary.summarize", new_callable=AsyncMock
        ) as mock:
            mock.side_effect = Exception("LLM failed")
            result = await summarize_content_fn(content="text")
            assert "Error" in result
