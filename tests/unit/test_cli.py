"""Unit tests for CLI — mocked, no I/O."""
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from click.testing import CliRunner

from content_core.cli import cli, _build_input, _get_content


class TestBuildInput:
    """Test the _build_input helper."""

    def test_url_detected(self):
        inp = _build_input("https://example.com")
        assert inp.url == "https://example.com"
        assert inp.file_path is None
        assert inp.content is None

    def test_file_detected(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        inp = _build_input(str(f))
        assert inp.file_path == str(f)
        assert inp.url is None

    def test_text_fallback(self):
        inp = _build_input("just some text")
        assert inp.content == "just some text"
        assert inp.url is None
        assert inp.file_path is None


class TestGetContent:
    """Test the _get_content helper."""

    def test_returns_content_when_provided(self):
        assert _get_content("hello") == "hello"

    def test_exits_on_empty_content(self):
        with pytest.raises(SystemExit):
            _get_content("")


class TestExtractCommand:
    """Test extract command with mocked extraction."""

    def test_extract_calls_extract_content(self):
        runner = CliRunner()
        from content_core.common.state import ExtractionOutput

        with patch(
            "content_core.extraction.extract_content",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="extracted"),
        ):
            result = runner.invoke(cli, ["extract", "hello"])
            assert result.exit_code == 0
            assert "extracted" in result.output

    def test_extract_json_format(self):
        runner = CliRunner()
        from content_core.common.state import ExtractionOutput

        with patch(
            "content_core.extraction.extract_content",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="test", title="t"),
        ):
            result = runner.invoke(cli, ["extract", "--format", "json", "hello"])
            assert result.exit_code == 0
            assert '"content"' in result.output

    def test_extract_with_engine_passes_config(self):
        runner = CliRunner()
        from content_core.common.state import ExtractionOutput

        with patch(
            "content_core.extraction.extract_content",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="ok"),
        ) as mock_extract:
            result = runner.invoke(cli, ["extract", "--engine", "firecrawl", "hello"])
            assert result.exit_code == 0
            # Verify config was passed with the engine
            _, kwargs = mock_extract.call_args
            assert kwargs["config"] is not None
            assert kwargs["config"].url_engine == "firecrawl"

    def test_extract_without_engine_no_config(self):
        runner = CliRunner()
        from content_core.common.state import ExtractionOutput

        with patch(
            "content_core.extraction.extract_content",
            new_callable=AsyncMock,
            return_value=ExtractionOutput(content="ok"),
        ) as mock_extract:
            result = runner.invoke(cli, ["extract", "hello"])
            assert result.exit_code == 0
            # config should be None (no --engine flag)
            _, kwargs = mock_extract.call_args
            assert kwargs.get("config") is None


class TestSummarizeCommand:
    """Test summarize command with mocked summarization."""

    def test_summarize_calls_summarize_fn(self):
        runner = CliRunner()
        with patch(
            "content_core.content.summary.summarize",
            new_callable=AsyncMock,
            return_value="summary text",
        ):
            result = runner.invoke(cli, ["summarize", "long text"])
            assert result.exit_code == 0

    def test_summarize_with_stdin(self):
        runner = CliRunner()
        with patch(
            "content_core.content.summary.summarize",
            new_callable=AsyncMock,
            return_value="summary",
        ):
            result = runner.invoke(cli, ["summarize"], input="piped text")
            assert result.exit_code == 0
