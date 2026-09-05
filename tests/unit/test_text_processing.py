"""Unit tests for content_core.processors.text."""

from unittest.mock import AsyncMock, patch

import pytest

from content_core.config import ContentCoreConfig
from content_core.processors.text import (
    detect_html,
    extract_html_title,
    extract_text_file,
    process_text,
    strip_html_head,
)


@pytest.fixture
def config():
    return ContentCoreConfig()


class TestProcessText:
    async def test_plain_text_returned_unchanged(self, config):
        result = await process_text("Hello, world!", config)
        assert result.content == "Hello, world!"
        assert result.source_type == "text"
        assert result.identified_type == "text/plain"

    async def test_html_content_converted_to_markdown(self, config):
        html = "<h1>Title</h1><p>Body</p>"
        result = await process_text(html, config)
        # markdownify converts h1 to "# Title\n\n" and p to "Body\n\n"
        assert "Title" in result.content
        assert "Body" in result.content
        assert result.source_type == "text"

    async def test_minimal_html_below_threshold_unchanged(self, config):
        text = "Hello <br> world"
        result = await process_text(text, config)
        # Only 1 tag, below threshold of 2
        assert result.content == text

    async def test_empty_string_returns_empty_output(self, config):
        result = await process_text("", config)
        assert result.content == ""
        assert result.source_type == "text"
        assert result.identified_type == "text/plain"


class TestDetectHtml:
    def test_headings_and_paragraphs_detected(self):
        html = "<h1>Title</h1><p>Paragraph text</p>"
        assert detect_html(html) is True

    def test_plain_text_not_detected(self):
        assert detect_html("Just some plain text with no tags") is False

    def test_single_tag_below_threshold(self):
        assert detect_html("Hello <br> world") is False

    def test_multiple_structural_tags_detected(self):
        html = "<div>Section</div><p>Text</p><ul><li>Item</li></ul>"
        assert detect_html(html) is True

    def test_doctype_document_detected_regardless_of_tag_count(self):
        html = "<!DOCTYPE html><html><head><title>T</title></head><body><p>Hi</p></body></html>"
        assert detect_html(html) is True

    def test_html_root_tag_detected(self):
        assert detect_html("<html><body>bare</body></html>") is True

    def test_leading_comment_before_doctype_detected(self):
        assert detect_html("<!-- generated -->\n<!doctype html><html></html>") is True

    def test_html_mentioned_mid_text_not_detected(self):
        assert detect_html("the <html> tag is where a document starts") is False


class TestExtractTextFile:
    async def test_reads_file_content(self, config):
        file_content = "This is the file content."
        with patch(
            "content_core.processors.text.asyncio.get_event_loop"
        ) as mock_loop:
            mock_executor = AsyncMock(return_value=file_content)
            mock_loop.return_value.run_in_executor = mock_executor

            result = await extract_text_file("/fake/path.txt", config)
            assert result.content == file_content
            assert result.source_type == "file"
            assert result.identified_type == "text/plain"

    async def test_nonexistent_file_raises_error(self, config):
        with patch(
            "content_core.processors.text.asyncio.get_event_loop"
        ) as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=FileNotFoundError("File not found at /no/such/file.txt")
            )

            with pytest.raises(FileNotFoundError):
                await extract_text_file("/no/such/file.txt", config)


class TestExtractHtmlTitle:
    def test_title_extracted(self):
        assert extract_html_title("<html><head><title>My Page</title></head></html>") == "My Page"

    def test_title_whitespace_stripped(self):
        html = "<html><head><title>\n   Spaced   Title \n</title></head></html>"
        assert extract_html_title(html) == "Spaced   Title"

    def test_title_entities_decoded(self):
        html = "<title>Tom &amp; Jerry&#39;s</title>"
        assert extract_html_title(html) == "Tom & Jerry's"

    def test_missing_title_returns_empty(self):
        assert extract_html_title("<html><body><p>No title</p></body></html>") == ""

    def test_empty_title_returns_empty(self):
        assert extract_html_title("<title>   </title>") == ""


class TestStripHtmlHead:
    def test_head_block_removed(self):
        html = "<html><HEAD><title>T</title>\n<style>p{}</style></HEAD><body><p>x</p></body></html>"
        assert strip_html_head(html) == "<html><body><p>x</p></body></html>"

    def test_no_head_unchanged(self):
        html = "<html><body><p>x</p></body></html>"
        assert strip_html_head(html) == html

    async def test_title_does_not_leak_into_content(self, config):
        html = "<html><head><title>Leaky</title></head><body><h1>Heading</h1><p>Body</p></body></html>"
        result = await process_text(html, config)
        assert result.title == "Leaky"
        assert not result.content.lstrip().startswith("Leaky")
        assert "Leaky" not in result.content
        assert "Heading" in result.content
