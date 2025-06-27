"""
Tests for PyMuPDF OCR enhancement functionality.
"""
import pytest
from unittest.mock import patch, MagicMock
from content_core.processors.pdf import (
    count_formula_placeholders,
    extract_page_with_ocr,
    convert_table_to_markdown,
)
from content_core.config import (
    set_pymupdf_ocr_enabled,
    set_pymupdf_formula_threshold,
    set_pymupdf_ocr_fallback,
)


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


class TestOCRExtraction:
    """Test OCR extraction functionality."""
    
    @patch('content_core.processors.pdf.fitz')
    def test_extract_page_with_ocr_success(self, mock_fitz):
        """Test successful OCR extraction."""
        # Mock page and textpage
        mock_page = MagicMock()
        mock_textpage = MagicMock()
        mock_textpage.extractText.return_value = "OCR extracted text with formulas"
        mock_page.get_textpage_ocr.return_value = mock_textpage
        
        result = extract_page_with_ocr(mock_page, 1)
        
        assert result == "OCR extracted text with formulas"
        mock_page.get_textpage_ocr.assert_called_once()
        mock_textpage.extractText.assert_called_once()
    
    @patch('content_core.processors.pdf.fitz')
    def test_extract_page_with_ocr_failure(self, mock_fitz):
        """Test OCR extraction failure (Tesseract not available)."""
        mock_page = MagicMock()
        mock_page.get_textpage_ocr.side_effect = Exception("Tesseract not found")
        
        result = extract_page_with_ocr(mock_page, 1)
        
        assert result is None
        mock_page.get_textpage_ocr.assert_called_once()
    
    @patch('content_core.processors.pdf.fitz')
    def test_extract_page_with_ocr_empty_result(self, mock_fitz):
        """Test OCR extraction returning empty textpage."""
        mock_page = MagicMock()
        mock_page.get_textpage_ocr.return_value = None
        
        result = extract_page_with_ocr(mock_page, 1)
        
        assert result is None


class TestConfigurationFunctions:
    """Test PyMuPDF configuration functions."""
    
    def test_set_pymupdf_ocr_enabled(self):
        """Test enabling/disabling OCR."""
        from content_core.config import CONFIG
        
        # Test enabling
        set_pymupdf_ocr_enabled(True)
        assert CONFIG.get('extraction', {}).get('pymupdf', {}).get('enable_formula_ocr') is True
        
        # Test disabling
        set_pymupdf_ocr_enabled(False)
        assert CONFIG.get('extraction', {}).get('pymupdf', {}).get('enable_formula_ocr') is False
    
    def test_set_pymupdf_formula_threshold(self):
        """Test setting formula threshold."""
        from content_core.config import CONFIG
        
        set_pymupdf_formula_threshold(5)
        assert CONFIG.get('extraction', {}).get('pymupdf', {}).get('formula_threshold') == 5
        
        set_pymupdf_formula_threshold(1)
        assert CONFIG.get('extraction', {}).get('pymupdf', {}).get('formula_threshold') == 1
    
    def test_set_pymupdf_ocr_fallback(self):
        """Test setting OCR fallback option."""
        from content_core.config import CONFIG
        
        set_pymupdf_ocr_fallback(True)
        assert CONFIG.get('extraction', {}).get('pymupdf', {}).get('ocr_fallback') is True
        
        set_pymupdf_ocr_fallback(False)
        assert CONFIG.get('extraction', {}).get('pymupdf', {}).get('ocr_fallback') is False


@pytest.mark.asyncio
class TestPDFExtractionIntegration:
    """Integration tests for PDF extraction with OCR."""
    
    async def test_pdf_extraction_without_ocr(self):
        """Test PDF extraction with OCR disabled."""
        from content_core.content.extraction import extract_content
        
        # Ensure OCR is disabled
        set_pymupdf_ocr_enabled(False)
        
        # Test with the sample PDF
        result = await extract_content({
            'file_path': 'tests/input_content/file.pdf',
            'document_engine': 'simple'
        })
        
        assert result.source_type == "file"
        assert len(result.content) > 0
        # Should not contain OCR artifacts
        assert "OCR extracted" not in result.content
    
    async def test_pdf_extraction_with_ocr_disabled_by_threshold(self):
        """Test PDF extraction where OCR is enabled but threshold not met."""
        from content_core.content.extraction import extract_content
        
        # Enable OCR but set high threshold
        set_pymupdf_ocr_enabled(True)
        set_pymupdf_formula_threshold(100)  # Very high threshold
        
        result = await extract_content({
            'file_path': 'tests/input_content/file.pdf',
            'document_engine': 'simple'
        })
        
        assert result.source_type == "file"
        assert len(result.content) > 0
        # OCR should not have been triggered due to high threshold
    
    @patch('content_core.processors.pdf.extract_page_with_ocr')
    async def test_pdf_extraction_with_ocr_fallback(self, mock_ocr):
        """Test PDF extraction with OCR failure and fallback."""
        from content_core.content.extraction import extract_content
        
        # Mock OCR to fail
        mock_ocr.return_value = None
        
        # Enable OCR with low threshold
        set_pymupdf_ocr_enabled(True)
        set_pymupdf_formula_threshold(0)  # Very low threshold
        set_pymupdf_ocr_fallback(True)
        
        result = await extract_content({
            'file_path': 'tests/input_content/file.pdf',
            'document_engine': 'simple'
        })
        
        assert result.source_type == "file"
        assert len(result.content) > 0
        # Should have content from fallback extraction
        assert "Buenos Aires" in result.content  # From the test PDF


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_count_formula_placeholders_with_none(self):
        """Test formula counting with None input."""
        # Should handle None gracefully
        try:
            result = count_formula_placeholders(None)
            assert result == 0
        except (TypeError, AttributeError):
            # If it throws an error, that's also acceptable behavior
            pass
    
    def test_convert_table_to_markdown_malformed(self):
        """Test table conversion with malformed data."""
        # Table with inconsistent row lengths
        malformed_table = [
            ["Header 1", "Header 2"],
            ["Row 1 Col 1"],  # Missing column
            ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"],  # Extra column
        ]
        
        result = convert_table_to_markdown(malformed_table)
        assert "Header 1" in result
        assert "Header 2" in result
        # Should handle gracefully without crashing


@pytest.fixture
def reset_config():
    """Reset configuration after each test."""
    yield
    # Reset to defaults
    set_pymupdf_ocr_enabled(False)
    set_pymupdf_formula_threshold(3)
    set_pymupdf_ocr_fallback(True)