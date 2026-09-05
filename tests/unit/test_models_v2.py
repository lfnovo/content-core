"""Tests for content_core.common.state."""
from __future__ import annotations


from content_core.common.state import ExtractionInput, ExtractionOutput


# --- ExtractionInput ---


class TestExtractionInput:
    def test_no_fields_set(self):
        inp = ExtractionInput()
        assert inp.content is None
        assert inp.file_path is None
        assert inp.url is None

    def test_url_set(self):
        inp = ExtractionInput(url="https://example.com")
        assert inp.url == "https://example.com"
        assert inp.content is None
        assert inp.file_path is None

    def test_file_path_set(self):
        inp = ExtractionInput(file_path="/tmp/doc.pdf")
        assert inp.file_path == "/tmp/doc.pdf"
        assert inp.content is None
        assert inp.url is None

    def test_content_set(self):
        inp = ExtractionInput(content="Hello world")
        assert inp.content == "Hello world"
        assert inp.file_path is None
        assert inp.url is None


# --- ExtractionOutput ---


class TestExtractionOutput:
    def test_default_values(self):
        out = ExtractionOutput()
        assert out.content == ""
        assert out.title == ""
        assert out.source_type == ""
        assert out.identified_type == ""
        assert out.metadata == {}

    def test_all_fields_populated(self):
        out = ExtractionOutput(
            content="Some extracted text",
            title="My Document",
            source_type="url",
            identified_type="article",
            metadata={"author": "Jane", "word_count": 500},
        )
        assert out.content == "Some extracted text"
        assert out.title == "My Document"
        assert out.source_type == "url"
        assert out.identified_type == "article"
        assert out.metadata == {"author": "Jane", "word_count": 500}

    def test_metadata_default_not_shared(self):
        out1 = ExtractionOutput()
        out2 = ExtractionOutput()
        out1.metadata["key"] = "value"
        assert "key" not in out2.metadata
