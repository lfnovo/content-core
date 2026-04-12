"""Unit tests for content_core.processors.document.epub."""
from unittest.mock import MagicMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.document.epub import extract_epub_file


class TestExtractEpubFile:
    @pytest.fixture
    def config(self):
        return ContentCoreConfig()

    async def test_successful_extraction(self, config):
        mock_epub = MagicMock()
        mock_epub.to_markdown.return_value = "# Chapter 1\nSome content"
        with patch(
            "content_core.processors.document.epub.read_epub",
            return_value=mock_epub,
        ):
            result = await extract_epub_file("/fake/book.epub", config)
            assert result.content == "# Chapter 1\nSome content"
            assert result.source_type == "file"
            assert result.identified_type == "application/epub+zip"

    async def test_empty_content(self, config):
        mock_epub = MagicMock()
        mock_epub.to_markdown.return_value = ""
        with patch(
            "content_core.processors.document.epub.read_epub",
            return_value=mock_epub,
        ):
            result = await extract_epub_file("/fake/book.epub", config)
            assert result.content == ""

    async def test_file_not_found_raises(self, config):
        with patch(
            "content_core.processors.document.epub.read_epub",
            side_effect=FileNotFoundError("not found"),
        ):
            with pytest.raises(FileNotFoundError):
                await extract_epub_file("/no/such/file.epub", config)
