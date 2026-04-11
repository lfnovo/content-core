"""Tests for content_core.models_v2 and content_core.processors.protocol."""
from __future__ import annotations

import pytest

from content_core.config import ContentCoreConfig
from content_core.models_v2 import ExtractionInput, ExtractionOutput
from content_core.processors.protocol import Processor


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


# --- Processor Protocol ---


class TestProcessorProtocol:
    def test_valid_processor_satisfies_protocol(self):
        class MyProcessor:
            async def extract(
                self, source: str, config: ContentCoreConfig
            ) -> ExtractionOutput:
                return ExtractionOutput(content=source)

        assert isinstance(MyProcessor(), Processor)

    def test_missing_extract_does_not_satisfy_protocol(self):
        class NotAProcessor:
            pass

        assert not isinstance(NotAProcessor(), Processor)
