"""Tests for the new unified CLI."""
import pytest
from click.testing import CliRunner

from content_core.cli import cli


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "extract" in result.output
        assert "summarize" in result.output
        assert "mcp" in result.output

    def test_extract_text(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["extract", "Hello world"])
        assert result.exit_code == 0
        assert "Hello world" in result.output

    def test_extract_json_format(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["extract", "--format", "json", "Hello world"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output)
        assert "content" in data

    def test_extract_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["extract", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output
        assert "--engine" in result.output

    def test_summarize_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["summarize", "--help"])
        assert result.exit_code == 0
        assert "--context" in result.output

    def test_extract_no_args(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["extract"])
        assert result.exit_code != 0

    def test_extract_with_engine_flag(self):
        """Test --engine flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["extract", "--engine", "simple", "Hello"])
        assert result.exit_code == 0

    def test_extract_file_input(self, fixtures_dir):
        """Test extracting from a local file."""
        md_file = fixtures_dir / "file.md"
        if not md_file.exists():
            pytest.skip("Fixture not found")
        runner = CliRunner()
        result = runner.invoke(cli, ["extract", str(md_file)])
        assert result.exit_code == 0
        assert len(result.output) > 0

    def test_summarize_stdin(self):
        """Test summarize reads from stdin."""
        runner = CliRunner()
        result = runner.invoke(cli, ["summarize"], input="Some text to summarize")
        # May fail without LLM API key, but should not crash on input parsing
        # Just verify it attempts to process (exit_code 0 or error from LLM, not from CLI parsing)
        assert "Error: No content provided" not in result.output

    def test_extract_debug_flag(self):
        """Test --debug flag is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--debug", "extract", "Hello"])
        assert result.exit_code == 0
