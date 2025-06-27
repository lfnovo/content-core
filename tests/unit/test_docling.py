import os
import pytest
from types import SimpleNamespace
from content_core.processors.docling import extract_with_docling, DOCLING_AVAILABLE
from content_core.common.state import ProcessSourceState

class DummyDoc:
    def __init__(self, content):
        self._content = content
    def to_markdown(self):
        return "md:" + self._content
    def to_html(self):
        return "<p>" + self._content + "</p>"
    def to_json(self):
        return '{"c":"' + self._content + '"}'
    export_to_markdown = to_markdown
    export_to_html = to_html
    export_to_json = to_json

class DummyConverter:
    def convert(self, source):
        if os.path.exists(source):
            return SimpleNamespace(document=DummyDoc("file:" + source))
        return SimpleNamespace(document=DummyDoc("blk:" + source))

@pytest.fixture(autouse=True)
def patch_converter(monkeypatch):
    monkeypatch.setattr(
        "content_core.processors.docling.DocumentConverter",
        DummyConverter,
    )

@pytest.mark.asyncio
@pytest.mark.skipif(not DOCLING_AVAILABLE, reason="Docling not installed")
async def test_extract_file(tmp_path):
    # File input with explicit markdown format
    fp = tmp_path / "test.txt"
    fp.write_text("hello world")
    state = ProcessSourceState(file_path=str(fp), metadata={"docling_format": "markdown"})
    new_state = await extract_with_docling(state)
    assert new_state.content == "md:file:" + str(fp)

@pytest.mark.asyncio
@pytest.mark.skipif(not DOCLING_AVAILABLE, reason="Docling not installed")
async def test_extract_block_html():
    # Block input with HTML format
    state = ProcessSourceState(content="block content", metadata={"docling_format": "html"})
    new_state = await extract_with_docling(state)
    assert new_state.content == "<p>blk:block content</p>"

@pytest.mark.asyncio
@pytest.mark.skipif(not DOCLING_AVAILABLE, reason="Docling not installed")
async def test_default_to_markdown():
    # Default format should fallback to markdown
    state = ProcessSourceState(content="plain text")
    new_state = await extract_with_docling(state)
    assert new_state.content == "md:blk:plain text"
    assert new_state.metadata["docling_format"] == "markdown"
