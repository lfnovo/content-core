"""Critical tests for FileDetector class - Top priority test cases."""
import pytest
from pathlib import Path
from content_core.content.identification import FileDetector
from content_core.common.exceptions import UnsupportedTypeException


class TestFileDetectorCritical:
    """Top 10 critical tests for the FileDetector improvements."""
    
    @pytest.fixture
    def detector(self):
        """Create a FileDetector instance."""
        return FileDetector()
    
    # Test 1: JSON Detection with Strong Indicators
    @pytest.mark.asyncio
    async def test_json_detection_pretty_printed(self, detector, tmp_path):
        """Test detection of pretty-printed JSON with strong indicators."""
        json_file = tmp_path / "data.json"
        json_file.write_text('''{
  "name": "test",
  "active": true,
  "count": 42,
  "items": [
    {"id": 1, "value": "first"},
    {"id": 2, "value": "second"}
  ]
}''')
        detected = await detector.detect(str(json_file))
        assert detected == "application/json"
    
    # Test 2: JSON False Positive Prevention
    @pytest.mark.asyncio
    async def test_json_reject_javascript(self, detector, tmp_path):
        """Test that JavaScript files starting with { are not detected as JSON."""
        js_file = tmp_path / "script.js"
        js_file.write_text('''{
    const config = {
        apiUrl: "https://api.example.com",
        timeout: 5000
    };
    
    function init() {
        console.log("Initializing...");
    }
}''')
        detected = await detector.detect(str(js_file))
        assert detected == "text/plain"  # Should fall back to plain text
    
    # Test 3: Text-based format detection (YAML/Markdown)
    @pytest.mark.asyncio
    async def test_yaml_front_matter_in_markdown(self, detector, tmp_path):
        """Test that files with YAML front matter are detected as text-based."""
        md_file = tmp_path / "post.md"
        md_file.write_text('''---
title: My Blog Post
author: John Doe
date: 2024-01-01
tags:
  - python
  - testing
---

# Introduction

This is a blog post with YAML front matter.

## Section 1

Some content here with **bold** and *italic* text.
''')
        detected = await detector.detect(str(md_file))
        # Both text/plain and text/yaml are valid text formats
        assert detected in ["text/plain", "text/yaml"]
    
    # Test 4: MP4 Detection with ftyp Box
    @pytest.mark.asyncio
    async def test_mp4_detection_flexible_ftyp(self, detector, tmp_path):
        """Test MP4 detection with various ftyp brands without fixed sizes."""
        # Test MP4 with isom brand
        mp4_file = tmp_path / "video.mp4"
        # Minimal MP4 structure: size(4) + 'ftyp'(4) + brand(4)
        mp4_file.write_bytes(b'\x00\x00\x00\x18ftypiso5\x00\x00\x00\x00')
        detected = await detector.detect(str(mp4_file))
        assert detected == "video/mp4"
        
        # Test M4A audio
        m4a_file = tmp_path / "audio.m4a"
        m4a_file.write_bytes(b'\x00\x00\x00\x20ftypM4A \x00\x00\x00\x00')
        detected = await detector.detect(str(m4a_file))
        assert detected == "audio/mp4"
    
    # Test 5: JPEG Detection Order
    @pytest.mark.asyncio
    async def test_jpeg_signature_priority(self, detector, tmp_path):
        """Test JPEG detection with various signatures in correct order."""
        # JPEG with EXIF (common in photos)
        exif_jpg = tmp_path / "photo.jpg"
        exif_jpg.write_bytes(b'\xff\xd8\xff\xe1\x00\x0fExif\x00\x00MM\x00*')
        detected = await detector.detect(str(exif_jpg))
        assert detected == "image/jpeg"
        
        # JPEG with Adobe marker
        adobe_jpg = tmp_path / "adobe.jpg"
        adobe_jpg.write_bytes(b'\xff\xd8\xff\xe2\x00\x0eAdobe\x00d\x80\x00\x00')
        detected = await detector.detect(str(adobe_jpg))
        assert detected == "image/jpeg"
    
    # Test 6: Unicode Handling with Replace Strategy
    @pytest.mark.asyncio
    async def test_unicode_handling_with_invalid_bytes(self, detector, tmp_path):
        """Test handling of files with invalid UTF-8 sequences."""
        mixed_file = tmp_path / "mixed.txt"
        # Write text with invalid UTF-8 bytes
        mixed_file.write_bytes(b'Valid ASCII text\n\xff\xfe\xfd\xfcInvalid UTF-8\nMore valid text')
        
        # Should not raise exception and should detect as text
        detected = await detector.detect(str(mixed_file))
        assert detected == "text/plain"
    
    # Test 7: ZIP-based Office Format Detection
    @pytest.mark.asyncio
    async def test_docx_detection_via_zip_content(self, detector, tmp_path):
        """Test DOCX detection by inspecting ZIP content."""
        import zipfile
        
        docx_file = tmp_path / "document.docx"
        with zipfile.ZipFile(docx_file, 'w') as zf:
            # Minimal DOCX structure
            zf.writestr('[Content_Types].xml', '<?xml version="1.0"?>')
            zf.writestr('word/document.xml', '<?xml version="1.0"?>')
            zf.writestr('word/styles.xml', '<?xml version="1.0"?>')
        
        detected = await detector.detect(str(docx_file))
        assert detected == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    
    # Test 8: YAML vs JSON Ambiguity
    @pytest.mark.asyncio
    async def test_yaml_key_value_detection(self, detector, tmp_path):
        """Test YAML detection with multiple key-value pairs."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text('''database:
  host: localhost
  port: 5432
  name: myapp
  
cache:
  type: redis
  ttl: 3600
  
features:
  - authentication
  - logging
  - monitoring
''')
        detected = await detector.detect(str(yaml_file))
        # YAML can be detected as either text/yaml or text/plain - both are valid
        assert detected in ["text/yaml", "text/plain"]
    
    # Test 9: CSV Detection
    @pytest.mark.asyncio
    async def test_csv_detection_consistent_commas(self, detector, tmp_path):
        """Test CSV detection based on consistent comma patterns."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text('''Name,Age,Email,City
John Doe,30,john@example.com,New York
Jane Smith,25,jane@example.com,Los Angeles
Bob Johnson,35,bob@example.com,Chicago
Alice Brown,28,alice@example.com,Houston
''')
        detected = await detector.detect(str(csv_file))
        assert detected == "text/csv"
    
    # Test 10: Error Handling for Edge Cases
    @pytest.mark.asyncio
    async def test_error_handling_nonexistent_file(self, detector):
        """Test proper error handling for non-existent files."""
        with pytest.raises(FileNotFoundError):
            await detector.detect("/path/that/does/not/exist.txt")
    
    @pytest.mark.asyncio
    async def test_error_handling_directory(self, detector, tmp_path):
        """Test proper error handling when path is a directory."""
        with pytest.raises(ValueError, match="Not a file"):
            await detector.detect(str(tmp_path))