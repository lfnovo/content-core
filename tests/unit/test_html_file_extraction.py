"""End-to-end unit tests for local HTML file extraction via the text processor.

Uses real files under ``tmp_path`` (no network, no docling): identification,
routing and HTML-to-markdown conversion all run for real.
"""
from __future__ import annotations

import pytest

from content_core.config import ContentCoreConfig
from content_core.extraction import extract_content

HTML_WITH_TITLE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Tom &amp; Jerry&#39;s Page</title>
  <style>body { color: red; }</style>
</head>
<body>
  <h1>Main Heading</h1>
  <p>First paragraph with <a href="https://example.com">a link</a>.</p>
  <ul><li>one</li><li>two</li></ul>
</body>
</html>
"""

HTML_WITHOUT_TITLE = """<html>
<body>
  <h1>Untitled Heading</h1>
  <p>Some body text.</p>
</body>
</html>
"""


@pytest.fixture
def config():
    return ContentCoreConfig(document_engine="simple")


@pytest.mark.asyncio
async def test_html_file_converted_to_markdown_with_title(tmp_path, config):
    page = tmp_path / "page.html"
    page.write_text(HTML_WITH_TITLE, encoding="utf-8")

    result = await extract_content(file_path=str(page), config=config)

    assert result.source_type == "file"
    assert result.identified_type == "text/html"
    assert result.title == "Tom & Jerry's Page"
    assert "# Main Heading" in result.content
    assert "[a link](https://example.com)" in result.content
    assert "- one" in result.content
    # <head> contents must not leak into the body
    assert not result.content.lstrip().startswith("Tom")
    assert "Jerry" not in result.content
    assert "color: red" not in result.content


@pytest.mark.asyncio
async def test_html_file_without_title_falls_back_to_basename(tmp_path, config):
    page = tmp_path / "untitled.html"
    page.write_text(HTML_WITHOUT_TITLE, encoding="utf-8")

    result = await extract_content(file_path=str(page), config=config)

    assert result.identified_type == "text/html"
    assert result.title == "untitled.html"
    assert "# Untitled Heading" in result.content


@pytest.mark.asyncio
async def test_txt_file_unchanged(tmp_path, config):
    text = "Just plain text.\nSecond line with <br> a stray tag.\n"
    note = tmp_path / "note.txt"
    note.write_text(text, encoding="utf-8")

    result = await extract_content(file_path=str(note), config=config)

    assert result.identified_type == "text/plain"
    assert result.title == "note.txt"
    assert result.content == text


@pytest.mark.asyncio
async def test_minimal_html_file_still_gets_title(tmp_path, config):
    """A page whose body has fewer than two structural tags is still HTML."""
    page = tmp_path / "tiny.html"
    page.write_text(
        "<!DOCTYPE html><html><head><title>Tiny</title></head><body><p>Hi</p></body></html>",
        encoding="utf-8",
    )

    result = await extract_content(file_path=str(page), config=config)

    assert result.title == "Tiny"
    assert result.content.strip() == "Hi"


@pytest.mark.asyncio
async def test_legacy_charset_html_file_decodes_declared_encoding(tmp_path, config):
    page = tmp_path / "legacy.html"
    page.write_bytes(
        "<html><head><meta charset=\"windows-1252\"><title>Café</title></head>"
        "<body><p>Crème brûlée</p></body></html>".encode("cp1252")
    )

    result = await extract_content(file_path=str(page), config=config)

    assert result.title == "Café"
    assert "Crème brûlée" in result.content


@pytest.mark.asyncio
async def test_non_utf8_without_declared_charset_does_not_raise(tmp_path, config):
    page = tmp_path / "latin.html"
    page.write_bytes("<html><body><p>Ação</p><p>ok</p></body></html>".encode("latin-1"))

    result = await extract_content(file_path=str(page), config=config)

    assert "Ação" in result.content
