"""Tests for PDF helper functions."""
import pytest
from unittest.mock import patch, MagicMock
from content_core.processors.document.pdf import (
    count_formula_placeholders,
    convert_table_to_markdown,
)
from content_core.config import ContentCoreConfig


class TestFormulaDetection:
    """Test formula placeholder detection."""

    def test_count_formula_placeholders_none(self):
        """Test counting when no formulas present."""
        text = "This is regular text with no formulas."
        assert count_formula_placeholders(text) == 0

    def test_count_formula_placeholders_single(self):
        """Test counting single formula placeholder."""
        text = "Text before <!-- formula-not-decoded --> text after."
        assert count_formula_placeholders(text) == 1

    def test_count_formula_placeholders_multiple(self):
        """Test counting multiple formula placeholders."""
        text = """
        First formula: <!-- formula-not-decoded -->
        Some text.
        Second formula: <!-- formula-not-decoded -->
        More text.
        Third formula: <!-- formula-not-decoded -->
        """
        assert count_formula_placeholders(text) == 3

    def test_count_formula_placeholders_empty_text(self):
        """Test counting on empty text."""
        assert count_formula_placeholders("") == 0
        assert count_formula_placeholders(None) == 0


class TestTableConversion:
    """Test table to markdown conversion."""

    def test_convert_simple_table(self):
        """Test converting a simple table."""
        table_data = [
            ["Header 1", "Header 2", "Header 3"],
            ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"],
        ]

        result = convert_table_to_markdown(table_data)
        expected_lines = [
            "| Header 1 | Header 2 | Header 3 |",
            "| --- | --- | --- |",
            "| Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |",
            "| Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |",
        ]

        for line in expected_lines:
            assert line in result

    def test_convert_table_with_empty_cells(self):
        """Test converting table with empty cells."""
        table_data = [
            ["Name", "Age", "City"],
            ["John", "", "New York"],
            ["", "25", "Boston"],
        ]

        result = convert_table_to_markdown(table_data)
        assert "| John |  | New York |" in result
        assert "|  | 25 | Boston |" in result

    def test_convert_empty_table(self):
        """Test converting empty table."""
        assert convert_table_to_markdown([]) == ""
        assert convert_table_to_markdown(None) == ""
        assert convert_table_to_markdown([[]]) == ""

    def test_convert_table_with_only_empty_cells(self):
        """Test converting table with only empty or whitespace cells."""
        empty_table = [
            ["", " ", "   "],
            [None, "", ""],
            ["  ", None, " "],
        ]
        # Should still create a table structure even with empty cells
        result = convert_table_to_markdown(empty_table)
        assert "|" in result  # Should have table structure
        assert "---" in result  # Should have separator


@pytest.mark.asyncio
class TestPDFExtractionIntegration:
    """Integration tests for PDF extraction."""

    async def test_pdf_extraction(self):
        """Test PDF extraction."""
        from content_core.content.extraction import extract_content

        cfg = ContentCoreConfig(
            document_engine="simple",
        )

        result = await extract_content(
            file_path="tests/input_content/file.pdf",
            config=cfg,
        )

        assert result.source_type == "file"
        assert len(result.content) > 0
        assert "OCR extracted" not in result.content


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_count_formula_placeholders_with_none(self):
        """Test formula counting with None input."""
        try:
            result = count_formula_placeholders(None)
            assert result == 0
        except (TypeError, AttributeError):
            pass

    def test_convert_table_to_markdown_malformed(self):
        """Test table conversion with malformed data."""
        malformed_table = [
            ["Header 1", "Header 2"],
            ["Row 1 Col 1"],
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"],
        ]

        result = convert_table_to_markdown(malformed_table)
        assert "Header 1" in result
        assert "Header 2" in result
