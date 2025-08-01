"""Performance benchmarks for FileDetector class."""
import pytest
import time
from pathlib import Path
from content_core.content.identification import FileDetector


class TestFileDetectorPerformance:
    """Performance benchmarks for file detection."""
    
    @pytest.fixture
    def detector(self):
        """Create a FileDetector instance."""
        return FileDetector()
    
    @pytest.fixture
    def large_file(self, tmp_path):
        """Create a large test file (100MB)."""
        large_file = tmp_path / "large_file.bin"
        # Write 100MB of data (but with PDF signature at start)
        with open(large_file, 'wb') as f:
            f.write(b'%PDF-1.5\n')  # PDF signature
            # Write 100MB of random data
            chunk = b'0' * (1024 * 1024)  # 1MB chunk
            for _ in range(100):
                f.write(chunk)
        return large_file
    
    @pytest.mark.asyncio
    async def test_pdf_detection_performance(self, detector, tmp_path):
        """Test PDF detection is fast (should read only first 512 bytes)."""
        # Create a PDF file
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b'%PDF-1.5\n%\xE2\xE3\xCF\xD3\n' + b'0' * 1000)
        
        # Measure detection time
        start_time = time.perf_counter()
        detected = await detector.detect(str(pdf_file))
        end_time = time.perf_counter()
        
        # Should detect as PDF
        assert detected == "application/pdf"
        
        # Should be very fast (under 10ms for local file)
        detection_time_ms = (end_time - start_time) * 1000
        assert detection_time_ms < 10, f"PDF detection took {detection_time_ms:.2f}ms, expected < 10ms"
    
    @pytest.mark.asyncio
    async def test_large_file_performance(self, detector, large_file):
        """Test that large files don't cause performance issues."""
        # Measure detection time for 100MB file
        start_time = time.perf_counter()
        detected = await detector.detect(str(large_file))
        end_time = time.perf_counter()
        
        # Should detect as PDF
        assert detected == "application/pdf"
        
        # Should be fast even for large files (under 20ms)
        # This proves we're not reading the entire file
        detection_time_ms = (end_time - start_time) * 1000
        assert detection_time_ms < 20, f"Large file detection took {detection_time_ms:.2f}ms, expected < 20ms"
    
    @pytest.mark.asyncio 
    async def test_multiple_format_detection_performance(self, detector, tmp_path):
        """Test detection performance across multiple file types."""
        # Create test files
        files = {
            "test.jpg": b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'0' * 1000,
            "test.png": b'\x89PNG\r\n\x1a\n' + b'0' * 1000,
            "test.mp3": b'ID3\x03\x00\x00\x00' + b'0' * 1000,
            "test.zip": b'PK\x03\x04' + b'0' * 1000,
            "test.json": b'{"name": "test", "value": 123}',
            "test.txt": b'This is a plain text file\nWith multiple lines\n',
        }
        
        expected_types = {
            "test.jpg": "image/jpeg",
            "test.png": "image/png", 
            "test.mp3": "audio/mpeg",
            "test.zip": "application/zip",
            "test.json": "application/json",
            "test.txt": "text/plain",
        }
        
        # Create all files
        for filename, content in files.items():
            file_path = tmp_path / filename
            file_path.write_bytes(content)
        
        # Measure total detection time
        start_time = time.perf_counter()
        
        for filename, expected_type in expected_types.items():
            file_path = tmp_path / filename
            detected = await detector.detect(str(file_path))
            assert detected == expected_type
        
        end_time = time.perf_counter()
        
        # Should detect all 6 files quickly (under 50ms total)
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / len(files)
        
        assert total_time_ms < 50, f"Total detection time {total_time_ms:.2f}ms for {len(files)} files"
        assert avg_time_ms < 10, f"Average detection time {avg_time_ms:.2f}ms per file"
    
    @pytest.mark.asyncio
    async def test_text_detection_performance(self, detector, tmp_path):
        """Test text format detection performance."""
        # Create a large text file (1MB)
        text_file = tmp_path / "large.txt"
        text_content = "Line of text\n" * 100000  # ~1MB of text
        text_file.write_text(text_content)
        
        # Measure detection time
        start_time = time.perf_counter()
        detected = await detector.detect(str(text_file))
        end_time = time.perf_counter()
        
        # Should detect as plain text
        assert detected == "text/plain"
        
        # Should be fast (only reads first 1024 bytes)
        detection_time_ms = (end_time - start_time) * 1000
        assert detection_time_ms < 20, f"Text detection took {detection_time_ms:.2f}ms, expected < 20ms"