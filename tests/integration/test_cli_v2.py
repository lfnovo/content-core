"""Tests for the new unified CLI."""
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
