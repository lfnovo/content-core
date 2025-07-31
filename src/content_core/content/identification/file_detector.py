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
    
    # Configuration constants
    SIGNATURE_READ_SIZE = 512  # Bytes to read for binary signature detection
    TEXT_READ_SIZE = 1024      # Bytes to read for text content analysis
    
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
            b'%PDF': 'application/pdf',  # PDF document signature (hex: 25 50 44 46)
            
            # Images
            b'\xff\xd8\xff\xe0': 'image/jpeg',  # JPEG with JFIF header (JPEG File Interchange Format)
            b'\xff\xd8\xff\xe1': 'image/jpeg',  # JPEG with EXIF header (Exchangeable Image File Format)
            b'\xff\xd8\xff\xe2': 'image/jpeg',  # JPEG with Adobe header (Adobe JPEG)
            b'\xff\xd8\xff\xdb': 'image/jpeg',  # JPEG with DQT (Define Quantization Table) marker
            b'\xff\xd8': 'image/jpeg',  # Generic JPEG signature (Start of Image marker, must be last)
            b'\x89PNG\r\n\x1a\n': 'image/png',  # PNG signature (hex: 89 50 4E 47 0D 0A 1A 0A)
            b'GIF87a': 'image/gif',  # GIF version 87a
            b'GIF89a': 'image/gif',  # GIF version 89a (supports animation and transparency)
            b'II*\x00': 'image/tiff',  # TIFF little-endian (Intel byte order)
            b'MM\x00*': 'image/tiff',  # TIFF big-endian (Motorola byte order)
            b'BM': 'image/bmp',  # Windows Bitmap signature
            
            # Audio
            b'ID3': 'audio/mpeg',  # MP3 with ID3v2 metadata tag
            b'\xff\xfb': 'audio/mpeg',  # MP3 frame sync with MPEG-1 Layer 3
            b'\xff\xf3': 'audio/mpeg',  # MP3 frame sync with MPEG-2 Layer 3
            b'\xff\xf2': 'audio/mpeg',  # MP3 frame sync with MPEG-2.5 Layer 3
            b'RIFF': None,  # Resource Interchange File Format - requires further inspection (could be WAV, AVI, WebP)
            b'fLaC': 'audio/flac',  # Free Lossless Audio Codec signature
            
            # Video/Audio containers - these will be handled by ftyp detection
            # MP4/M4A/MOV use ftyp box at offset 4 for identification
            
            # Archive formats
            b'PK\x03\x04': 'application/zip',  # ZIP archive (also used by DOCX, XLSX, PPTX, JAR, etc.)
            b'PK\x05\x06': 'application/zip',  # Empty ZIP archive (End of Central Directory)
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
            # Documents
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/plain',  # Markdown treated as plain text (current behavior)
            '.markdown': 'text/plain',
            '.rst': 'text/plain',  # reStructuredText
            '.log': 'text/plain',
            
            # Web formats
            '.html': 'text/html',
            '.htm': 'text/html',
            '.xhtml': 'text/html',
            '.xml': 'text/xml',
            
            # Data formats
            '.json': 'application/json',
            '.yaml': 'text/yaml',
            '.yml': 'text/yaml',
            '.csv': 'text/csv',
            '.tsv': 'text/csv',  # Tab-separated values
            
            # Images
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.jpe': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp',
            '.ico': 'image/x-icon',
            '.svg': 'image/svg+xml',
            
            # Audio
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.wave': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.aac': 'audio/aac',
            '.ogg': 'audio/ogg',
            '.oga': 'audio/ogg',
            '.flac': 'audio/flac',
            '.wma': 'audio/x-ms-wma',
            
            # Video
            '.mp4': 'video/mp4',
            '.m4v': 'video/mp4',
            '.avi': 'video/x-msvideo',
            '.mov': 'video/quicktime',
            '.qt': 'video/quicktime',
            '.wmv': 'video/x-ms-wmv',
            '.flv': 'video/x-flv',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.mpg': 'video/mpeg',
            '.mpeg': 'video/mpeg',
            '.3gp': 'video/3gpp',
            
            # Office formats
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            
            # E-books
            '.epub': 'application/epub+zip',
            
            # Archives (basic detection - not expanded)
            '.zip': 'application/zip',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
            '.bz2': 'application/x-bzip2',
            '.7z': 'application/x-7z-compressed',
            '.rar': 'application/x-rar-compressed',
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
                # Read bytes for signature detection
                header = f.read(self.SIGNATURE_READ_SIZE)
                
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
                ftyp_brand = header[8:12]
                # Don't strip - check exact 4-byte brand
                if ftyp_brand == b'M4A ' or ftyp_brand.startswith(b'M4A'):
                    return 'audio/mp4'
                elif ftyp_brand in [b'mp41', b'mp42', b'isom', b'iso2', b'iso5', b'M4V ', b'M4VP']:
                    return 'video/mp4'
                elif ftyp_brand.startswith(b'qt'):
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
            # Read bytes for text content analysis
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(self.TEXT_READ_SIZE)
            
            if not content or len(content) < 10:
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
                    # HTML needs to be detected for routing
                    elif mime_type == 'text/html':
                        return mime_type
                    # For other text patterns (YAML, etc), just return text/plain
                    else:
                        return 'text/plain'
            
            # Check for CSV pattern (multiple comma-separated values)
            if self._looks_like_csv(content):
                return 'text/csv'
            
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
        # More robust JSON detection
        content = content.strip()
        if not (content.startswith('{') or content.startswith('[')):
            return False
        
        # Strong JSON indicators that are less likely in other formats
        strong_indicators = [
            '{\n  "',  # Pretty-printed JSON object
            '{\n\t"',  # Tab-indented JSON
            '{"',      # Compact JSON object
            '[\n  {',  # Pretty-printed JSON array
            '[{',      # Compact JSON array
            '": {',    # Nested object
            '": ['     # Nested array
        ]
        
        # Check for strong indicators
        for indicator in strong_indicators:
            if indicator in content[:200]:
                return True
        
        # Weaker indicators - require multiple matches
        json_patterns = ['":', '": ', '",', ', "', '"]', '"}']
        pattern_count = sum(1 for pattern in json_patterns if pattern in content[:200])
        
        # Check for JSON keywords but not in URLs or natural text
        json_keywords = ['true', 'false', 'null']
        keyword_count = 0
        content_lower = content[:200].lower()
        for kw in json_keywords:
            # Check if keyword appears as a value (not in URL or sentence)
            if f': {kw}' in content_lower or f':{kw}' in content_lower or f', {kw}' in content_lower:
                keyword_count += 1
        
        # Require stronger evidence to avoid false positives
        return pattern_count >= 3 or keyword_count >= 1
    
    
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