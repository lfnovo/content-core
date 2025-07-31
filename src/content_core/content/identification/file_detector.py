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
                    else:
                        return mime_type
            
            # Additional YAML detection (more patterns)
            if self._looks_like_yaml(content):
                return 'text/yaml'
            
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
        # More robust JSON detection
        content = content.strip()
        if not (content.startswith('{') or content.startswith('[')):
            return False
        
        # Check for JSON-like patterns in first 100 chars
        json_indicators = ['":', '": ', '",', ', "', '"]', '"}', '[]', '{}']
        indicator_count = sum(1 for ind in json_indicators if ind in content[:100])
        
        # Also check for common JSON keywords
        json_keywords = ['true', 'false', 'null']
        keyword_found = any(kw in content[:200].lower() for kw in json_keywords)
        
        return indicator_count >= 1 or keyword_found
    
    def _looks_like_yaml(self, content: str) -> bool:
        """Check if content looks like YAML format."""
        lines = content.split('\n')
        yaml_indicators = 0
        key_value_lines = 0
        
        # Don't detect YAML if it looks more like Markdown
        if self._looks_like_markdown(content):
            return False
        
        for line in lines[:20]:  # Check first 20 lines
            stripped = line.strip()
            # YAML document markers (strong indicator at start)
            if stripped == '---' or stripped == '...':
                if lines.index(line) < 3:  # Only count if near start
                    yaml_indicators += 3
            elif ':' in line and not line.strip().startswith('#'):
                # Check for key: value pattern
                parts = line.split(':', 1)
                if len(parts) == 2 and parts[0].strip() and not parts[0].strip().startswith('"'):
                    # Valid YAML key pattern
                    key = parts[0].strip()
                    if ' ' not in key or key.startswith('"') or key.startswith("'"):
                        yaml_indicators += 1
                        key_value_lines += 1
            elif stripped.startswith('- ') and len(stripped) > 2:
                yaml_indicators += 1
            elif stripped.startswith('#') and len(stripped) > 1:
                yaml_indicators += 0.3  # Comments are weak indicators
        
        # Need multiple key-value pairs for simple YAML detection
        if key_value_lines >= 2 and yaml_indicators >= 2:
            return True
            
        return yaml_indicators >= 3
    
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
        lines = content.split('\n')
        markdown_score = 0
        
        # Strong indicators (at start of line)
        for line in lines[:30]:  # Check first 30 lines
            stripped = line.strip()
            # Headers
            if stripped.startswith(('#', '##', '###', '####', '#####', '######')) and ' ' in stripped:
                markdown_score += 2
            # Lists
            elif stripped.startswith(('- ', '* ', '+ ')) or (len(stripped) >= 3 and stripped[0].isdigit() and stripped[1:3] in ['. ', ') ']):
                markdown_score += 1.5
            # Quotes
            elif stripped.startswith('> '):
                markdown_score += 1.5
            # Horizontal rules
            elif stripped in ['---', '***', '___'] and len(stripped) >= 3:
                markdown_score += 2
            # Code blocks
            elif stripped.startswith('```'):
                markdown_score += 2
        
        # Inline indicators (anywhere in content)
        content_sample = content[:1000]  # Check first 1000 chars
        
        # Links [text](url)
        if '[' in content_sample and '](' in content_sample:
            markdown_score += 1.5
        
        # Images ![alt](url)
        if '![' in content_sample and '](' in content_sample:
            markdown_score += 2
        
        # Bold/italic
        if '**' in content_sample or '__' in content_sample:
            markdown_score += 1
        if '*' in content_sample or '_' in content_sample:
            markdown_score += 0.5
        
        # Code spans
        if '`' in content_sample:
            markdown_score += 1
        
        # Tables (look for pipe characters in aligned patterns)
        for line in lines[:20]:
            if '|' in line and line.count('|') >= 2:
                markdown_score += 1.5
                break
        
        # Need significant evidence for Markdown
        return markdown_score >= 3
    
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