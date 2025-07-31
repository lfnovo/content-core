"""
Pure Python file type detection using magic bytes and content analysis.
Replaces libmagic dependency with a lightweight implementation.
"""

import os
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple

from content_core.common.exceptions import UnsupportedTypeException
from content_core.logging import logger


class FileDetector:
    """Pure Python file type detection using magic bytes and content analysis."""
    
    def __init__(self):
        """Initialize the FileDetector with signature mappings."""
        self.binary_signatures = self._load_binary_signatures()
        self.text_patterns = self._load_text_patterns()
        self.extension_mapping = self._load_extension_mapping()
        self.zip_content_patterns = self._load_zip_content_patterns()
    
    def _load_binary_signatures(self) -> Dict[bytes, str]:
        """Load binary file signatures (magic bytes) to MIME type mappings."""
        # Ordered by specificity - longer/more specific signatures first
        return {
            # PDF
            b'%PDF': 'application/pdf',
            
            # Images
            b'\xff\xd8\xff\xe0': 'image/jpeg',  # JPEG with JFIF
            b'\xff\xd8\xff\xe1': 'image/jpeg',  # JPEG with EXIF
            b'\xff\xd8\xff': 'image/jpeg',  # Generic JPEG
            b'\x89PNG\r\n\x1a\n': 'image/png',
            b'GIF87a': 'image/gif',
            b'GIF89a': 'image/gif',
            b'II*\x00': 'image/tiff',  # Little-endian TIFF
            b'MM\x00*': 'image/tiff',  # Big-endian TIFF
            b'BM': 'image/bmp',
            
            # Audio
            b'ID3': 'audio/mpeg',  # MP3 with ID3 tag
            b'\xff\xfb': 'audio/mpeg',  # MP3 without ID3
            b'\xff\xf3': 'audio/mpeg',  # MP3 without ID3 (alternate)
            b'\xff\xf2': 'audio/mpeg',  # MP3 without ID3 (alternate)
            b'RIFF': None,  # Special handling needed - could be WAV or AVI
            b'fLaC': 'audio/flac',  # FLAC audio
            
            # Video - MP4 family (check ftyp box at offset 4)
            b'\x00\x00\x00\x20ftypM4A': 'audio/mp4',  # M4A audio
            b'\x00\x00\x00\x1cftypM4A': 'audio/mp4',  # M4A audio variant
            b'\x00\x00\x00\x18ftypmp42': 'video/mp4',  # MP4 video
            b'\x00\x00\x00\x20ftypmp42': 'video/mp4',  # MP4 video variant
            b'\x00\x00\x00\x18ftypisom': 'video/mp4',  # MP4 ISO Base Media
            b'\x00\x00\x00\x20ftypisom': 'video/mp4',  # MP4 ISO Base Media variant
            b'\x00\x00\x00\x14ftypqt': 'video/quicktime',  # QuickTime
            
            # MOV files
            b'\x00\x00\x00\x14ftypqt  ': 'video/quicktime',
            
            # ZIP-based formats (need further inspection)
            b'PK\x03\x04': 'application/zip',  # Will be refined by ZIP content inspection
            b'PK\x05\x06': 'application/zip',  # Empty ZIP
        }
    
    def _load_text_patterns(self) -> Dict[str, str]:
        """Load text-based format detection patterns."""
        return {
            '<!DOCTYPE html': 'text/html',
            '<!doctype html': 'text/html',
            '<html': 'text/html',
            '<?xml': 'text/xml',
            '{': 'application/json',  # Will need more validation
            '[': 'application/json',  # Will need more validation
            '---\n': 'text/yaml',
            '---\r\n': 'text/yaml',
        }
    
    def _load_extension_mapping(self) -> Dict[str, str]:
        """Load file extension to MIME type mappings as fallback."""
        return {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/plain',  # Markdown treated as plain text (current behavior)
            '.markdown': 'text/plain',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xml': 'text/xml',
            '.json': 'application/json',
            '.yaml': 'text/yaml',
            '.yml': 'text/yaml',
            '.csv': 'text/csv',
            
            # Images
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            
            # Audio
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            
            # Video
            '.mp4': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            
            # Office formats
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            
            # EPUB
            '.epub': 'application/epub+zip',
        }
    
    def _load_zip_content_patterns(self) -> Dict[str, str]:
        """Load patterns for identifying ZIP-based formats by their content."""
        return {
            'word/': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xl/': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            'ppt/': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'META-INF/container.xml': 'application/epub+zip',
        }
    
    async def detect(self, file_path: str) -> str:
        """
        Detect file type using magic bytes and content analysis.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            MIME type string
            
        Raises:
            UnsupportedTypeException: If file type cannot be determined
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")
        
        # Try binary signature detection first
        mime_type = await self._detect_by_signature(file_path)
        if mime_type:
            logger.debug(f"Detected {file_path} as {mime_type} by signature")
            return mime_type
        
        # Try text-based detection
        mime_type = await self._detect_text_format(file_path)
        if mime_type:
            logger.debug(f"Detected {file_path} as {mime_type} by text analysis")
            return mime_type
        
        # Fallback to extension
        mime_type = self._detect_by_extension(file_path)
        if mime_type:
            logger.debug(f"Detected {file_path} as {mime_type} by extension")
            return mime_type
        
        # If all detection methods fail
        raise UnsupportedTypeException(f"Unable to determine file type for: {file_path}")
    
    async def _detect_by_signature(self, file_path: Path) -> Optional[str]:
        """Detect file type by binary signature (magic bytes)."""
        try:
            with open(file_path, 'rb') as f:
                # Read first 512 bytes
                header = f.read(512)
                
            if not header:
                return None
            
            # Check for exact signature matches
            for signature, mime_type in self.binary_signatures.items():
                if header.startswith(signature):
                    # Special handling for RIFF (could be WAV or AVI)
                    if signature == b'RIFF' and len(header) >= 12:
                        if header[8:12] == b'WAVE':
                            return 'audio/wav'
                        elif header[8:12] == b'AVI ':
                            return 'video/x-msvideo'
                    
                    # Special handling for ZIP-based formats
                    if mime_type == 'application/zip':
                        zip_mime = await self._detect_zip_format(file_path)
                        if zip_mime:
                            return zip_mime
                    
                    if mime_type:
                        return mime_type
            
            # Special check for MP4/MOV files with ftyp box
            if len(header) >= 12 and header[4:8] == b'ftyp':
                ftyp_brand = header[8:12].strip()
                if ftyp_brand in [b'M4A ', b'M4A\x00']:
                    return 'audio/mp4'
                elif ftyp_brand in [b'mp41', b'mp42', b'isom', b'iso2', b'M4V ', b'M4VP']:
                    return 'video/mp4'
                elif ftyp_brand in [b'qt  ', b'qt\x00\x00']:
                    return 'video/quicktime'
                else:
                    # Generic MP4 for other ftyp brands
                    return 'video/mp4'
            
            return None
            
        except Exception as e:
            logger.debug(f"Error reading file signature: {e}")
            return None
    
    async def _detect_zip_format(self, file_path: Path) -> Optional[str]:
        """Detect specific ZIP-based format (DOCX, XLSX, PPTX, EPUB)."""
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                namelist = zf.namelist()
                
                # Check for specific content patterns
                for pattern, mime_type in self.zip_content_patterns.items():
                    if any(name.startswith(pattern) for name in namelist):
                        return mime_type
                
                # If it's a valid ZIP but no specific pattern matched
                return 'application/zip'
                
        except zipfile.BadZipFile:
            logger.debug(f"Invalid ZIP file: {file_path}")
            return None
        except Exception as e:
            logger.debug(f"Error inspecting ZIP content: {e}")
            return None
    
    async def _detect_text_format(self, file_path: Path) -> Optional[str]:
        """Detect text-based formats by content analysis."""
        try:
            # Read first 1024 bytes as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(1024)
            
            if not content:
                return None
            
            # Strip whitespace for analysis
            content_stripped = content.strip()
            
            # Check for text patterns
            for pattern, mime_type in self.text_patterns.items():
                if content_stripped.lower().startswith(pattern.lower()):
                    # Special validation for JSON
                    if mime_type == 'application/json':
                        if self._is_valid_json_start(content_stripped):
                            return mime_type
                    else:
                        return mime_type
            
            # Check for CSV pattern (multiple comma-separated values)
            if self._looks_like_csv(content):
                return 'text/csv'
            
            # Check for Markdown indicators
            if self._looks_like_markdown(content):
                return 'text/plain'  # Markdown is treated as plain text
            
            # If it's readable text but no specific format detected
            if self._is_text_file(content):
                return 'text/plain'
            
            return None
            
        except UnicodeDecodeError:
            # Not a text file
            return None
        except Exception as e:
            logger.debug(f"Error analyzing text content: {e}")
            return None
    
    def _detect_by_extension(self, file_path: Path) -> Optional[str]:
        """Detect file type by extension as fallback."""
        extension = file_path.suffix.lower()
        return self.extension_mapping.get(extension)
    
    def _is_valid_json_start(self, content: str) -> bool:
        """Check if content starts like valid JSON."""
        # Simple check for JSON-like start
        return (content.startswith('{') or content.startswith('[')) and (
            '"' in content[:50] or "'" in content[:50]
        )
    
    def _looks_like_csv(self, content: str) -> bool:
        """Check if content looks like CSV format."""
        lines = content.split('\n', 5)[:5]  # Check first 5 lines
        if len(lines) < 2:
            return False
        
        # Count commas in each line
        comma_counts = [line.count(',') for line in lines if line.strip()]
        if not comma_counts:
            return False
        
        # CSV should have consistent comma counts
        return len(set(comma_counts)) == 1 and comma_counts[0] > 0
    
    def _looks_like_markdown(self, content: str) -> bool:
        """Check if content looks like Markdown format."""
        # Look for common Markdown patterns
        markdown_indicators = [
            '# ',  # Headers
            '## ',
            '### ',
            '- ',  # Lists
            '* ',
            '1. ',
            '[',  # Links
            '```',  # Code blocks
            '**',  # Bold
            '*',  # Italic (but not bullet point)
            '> ',  # Quotes
        ]
        
        # Count indicators
        indicator_count = sum(1 for indicator in markdown_indicators if indicator in content)
        
        # If multiple indicators found, likely Markdown
        return indicator_count >= 2
    
    def _is_text_file(self, content: str) -> bool:
        """Check if content appears to be plain text."""
        if not content or len(content) < 10:  # Need reasonable content
            return False
            
        # Check for high ratio of printable characters
        printable_chars = sum(1 for c in content if c.isprintable() or c.isspace())
        
        # Also check that it has reasonable line lengths (not binary data)
        lines = content.split('\n')
        max_line_length = max(len(line) for line in lines) if lines else 0
        
        # Text files typically have lines under 1000 chars and high printable ratio
        return (printable_chars / len(content) > 0.95 and 
                max_line_length < 1000 and 
                len(content) > 20)  # Minimum reasonable text file size


# Backward compatibility function
async def get_file_type(file_path: str) -> str:
    """
    Legacy function for compatibility with existing code.
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        MIME type string
        
    Raises:
        UnsupportedTypeException: If file type cannot be determined
    """
    detector = FileDetector()
    return await detector.detect(file_path)