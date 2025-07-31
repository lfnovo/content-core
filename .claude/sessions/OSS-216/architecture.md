# OSS-216: Remove libmagic Dependency - Architecture

## High-Level System Overview

### Current State (Before)
```
File Input → magic.from_file() → MIME Type → Content Router → Processor
                     ↑
                libmagic (C library)
```

### Target State (After)
```
File Input → file_detector.detect() → MIME Type → Content Router → Processor
                     ↑
              Pure Python Detection
```

## Affected Components

### 1. `/src/content_core/content/identification/__init__.py`
- **Current**: Single function `get_file_type()` using `magic.from_file()`
- **Change**: Replace with new detection module
- **Dependencies**: None (isolated module)

### 2. `/src/content_core/content/extraction/graph.py`
- **Current**: `file_type()` function using `magic.from_file()` at line 62
- **Change**: Replace with new detection function call
- **Dependencies**: Routes to various processors based on MIME type

### 3. `/pyproject.toml`
- **Current**: Dependencies on `python-magic>=0.4.27` and `python-magic-bin==0.4.14`
- **Change**: Remove both dependencies

## New Component Design

### File Detection Module (`/src/content_core/content/identification/file_detector.py`)

```python
class FileDetector:
    """Pure Python file type detection using magic bytes and content analysis."""
    
    def __init__(self):
        self.signatures = self._load_signatures()
        self.text_patterns = self._load_text_patterns()
    
    async def detect(self, file_path: str) -> str:
        """Main detection method returning MIME type."""
        # 1. Read first 512 bytes
        # 2. Check binary signatures
        # 3. If no match, analyze as text
        # 4. Fallback to extension mapping
        # 5. Raise UnsupportedTypeException if all fail

# Backward compatibility function
async def get_file_type(file_path: str) -> str:
    """Legacy function for compatibility."""
    detector = FileDetector()
    return await detector.detect(file_path)
```

### Signature Mappings

```python
BINARY_SIGNATURES = {
    # PDFs
    b'%PDF': 'application/pdf',
    
    # Office formats (ZIP-based)
    b'PK\x03\x04': 'application/zip',  # Will need content analysis
    
    # Images
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'II*\x00': 'image/tiff',
    b'MM\x00*': 'image/tiff',
    
    # Audio/Video
    b'ID3': 'audio/mpeg',
    b'\xff\xfb': 'audio/mpeg',
    b'RIFF': 'audio/wav',  # Also video/avi
    b'\x00\x00\x00\x14ftypM4A': 'audio/mp4',
    b'\x00\x00\x00\x18ftypmp4': 'video/mp4',
    b'\x00\x00\x00\x14ftypisom': 'video/mp4',
    
    # EPUB
    b'PK\x03\x04': 'application/epub+zip',  # Will need content analysis
}

# For ZIP-based formats, check internal structure
ZIP_CONTENT_PATTERNS = {
    'word/': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'xl/': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'ppt/': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'META-INF/container.xml': 'application/epub+zip',
}

# Text-based format detection
TEXT_PATTERNS = {
    '<!DOCTYPE html': 'text/html',
    '<html': 'text/html',
    '<?xml': 'text/xml',
    '{"': 'application/json',
    '[{': 'application/json',
    '---\n': 'text/yaml',
    '#': 'text/markdown',  # Weak, needs more context
}

# Extension fallback mapping
EXTENSION_MAPPING = {
    '.pdf': 'application/pdf',
    '.txt': 'text/plain',
    '.md': 'text/plain',  # Current behavior
    '.html': 'text/html',
    '.json': 'application/json',
    '.csv': 'text/csv',
    '.mp4': 'video/mp4',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.epub': 'application/epub+zip',
}
```

## Implementation Strategy

### Phase 1: Create Detection Module
1. Implement `FileDetector` class with all detection logic
2. Handle ZIP-based formats by checking internal structure
3. Implement robust text format detection
4. Add comprehensive logging for debugging

### Phase 2: Integration
1. Update `get_file_type()` to use new detector
2. Update `file_type()` in graph.py
3. Ensure all MIME type strings match expected values

### Phase 3: Cleanup
1. Remove magic imports
2. Update pyproject.toml dependencies
3. Run tests to ensure compatibility

## Patterns & Best Practices

### Error Handling
- Maintain existing `UnsupportedTypeException` behavior
- Add specific error messages for debugging
- Log detection attempts for troubleshooting

### Async Pattern
- Keep async interface for consistency
- Use `aiofiles` if needed for async file reading

### Extensibility
- Design for easy addition of new signatures
- Consider configuration file for custom mappings

## External Dependencies
- **None** - Pure Python implementation
- Uses only standard library: `os`, `pathlib`, `zipfile`

## Trade-offs & Alternatives

### Trade-offs
1. **Performance**: Slightly slower than libmagic C library, but acceptable per requirements
2. **Accuracy**: May have edge cases libmagic handles better, but covers all current use cases
3. **Maintenance**: More code to maintain, but removes deployment complexity

### Alternatives Considered
1. **python-magic-bin fork**: Still has binary dependencies
2. **filetype library**: Pure Python but limited format support
3. **Custom C extension**: Defeats purpose of removing binary dependencies

## Negative Consequences
1. **Potential edge cases**: Some obscure file formats might not be detected correctly
2. **Maintenance burden**: Need to update signatures for new formats
3. **Slightly larger codebase**: Adding ~200 lines of detection code

## Files to Edit/Create

### Create:
1. `/src/content_core/content/identification/file_detector.py` - Main detection logic

### Edit:
1. `/src/content_core/content/identification/__init__.py` - Update to use new detector
2. `/src/content_core/content/extraction/graph.py` - Replace magic.from_file() call
3. `/pyproject.toml` - Remove python-magic dependencies

### No Changes Needed:
- All processor files (they only check MIME types, don't detect them)
- Test files (will continue to work with same MIME types)