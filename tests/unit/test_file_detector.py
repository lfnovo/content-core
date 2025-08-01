"""Tests for FileDetector class."""
import pytest
from pathlib import Path
from content_core.content.identification import FileDetector


class TestFileDetectorPDF:
    """Test PDF file detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create a FileDetector instance."""
        return FileDetector()
    
    @pytest.fixture
    def test_pdf_path(self):
        """Get path to test PDF file."""
        return Path(__file__).parent.parent / "input_content" / "file.pdf"
    
    @pytest.mark.asyncio
    async def test_detect_pdf_file(self, detector, test_pdf_path):
        """Test detection of a valid PDF file."""
        # Ensure test file exists
        assert test_pdf_path.exists(), f"Test PDF file not found at {test_pdf_path}"
        
        # Detect file type
        detected_type = await detector.detect(str(test_pdf_path))
        
        # Assert it's detected as PDF
        assert detected_type == "application/pdf", f"Expected 'application/pdf', got '{detected_type}'"
    
    @pytest.mark.asyncio
    async def test_pdf_detection_with_wrong_extension(self, detector, test_pdf_path, tmp_path):
        """Test PDF detection works regardless of file extension."""
        # Copy PDF with wrong extension
        wrong_ext_path = tmp_path / "test.txt"
        wrong_ext_path.write_bytes(test_pdf_path.read_bytes())
        
        # Detect file type
        detected_type = await detector.detect(str(wrong_ext_path))
        
        # Should still detect as PDF based on content, not extension
        assert detected_type == "application/pdf", f"Expected 'application/pdf', got '{detected_type}'"
    
    @pytest.mark.asyncio
    async def test_pdf_detection_performance(self, detector, test_pdf_path):
        """Test PDF detection is performant (reads minimal bytes)."""
        import time
        
        # Measure detection time
        start_time = time.time()
        detected_type = await detector.detect(str(test_pdf_path))
        end_time = time.time()
        
        # Should be detected as PDF
        assert detected_type == "application/pdf"
        
        # Should be fast (under 100ms for signature-based detection)
        detection_time = (end_time - start_time) * 1000  # Convert to ms
        assert detection_time < 100, f"PDF detection took {detection_time:.2f}ms, expected < 100ms"