# OSS-216: Remove libmagic Dependency

If you are working on this feature, make sure to update this plan.md file as you go. 

## PHASE 1: Create Pure Python File Detection Module [Completed ✅]

Build the core file detection system to replace libmagic with pure Python implementation.

### Create file_detector.py with basic structure [Completed ✅]

Create `/src/content_core/content/identification/file_detector.py` with:
- FileDetector class skeleton
- Basic signature mappings for binary formats (PDF, images)
- Simple detect() method that reads first 512 bytes
- Raise UnsupportedTypeException for unknown types

### Implement binary format detection [Completed ✅]

Add detection for binary formats:
- PDF files (magic bytes: `%PDF`)
- Common image formats (JPEG, PNG, GIF, TIFF, BMP)
- Audio formats (MP3, WAV, M4A)
- Video formats (MP4, AVI, MOV)
- Test each format with sample files

### Implement ZIP-based format detection [Completed ✅]

Handle Office and EPUB formats that use ZIP containers:
- Detect ZIP magic bytes (`PK\x03\x04`)
- Use zipfile module to inspect internal structure
- Differentiate DOCX (word/), XLSX (xl/), PPTX (ppt/), EPUB (META-INF/container.xml)
- Handle corrupted or password-protected ZIP files gracefully

### Comments:
- Focus on accurate detection over performance
- Ensure all MIME types match exactly what libmagic returns
- **Implementation notes from Phase 1:**
  - Added comprehensive binary signatures with ordered checking (longer signatures first)
  - Implemented generic ftyp box detection for MP4/MOV files for better compatibility
  - Added FLAC audio format support
  - Special RIFF handling differentiates between WAV and AVI
  - Text detection requires minimum content length to avoid false positives
  - All core file types tested and working correctly

## PHASE 2: Text Format Detection and Fallbacks [Completed ✅]

Implement text-based format detection and extension fallback mechanism.

### Add text format detection [Completed ✅]

Implement content analysis for text formats:
- HTML detection (DOCTYPE, <html tags)
- XML detection (<?xml declaration)
- JSON detection (starts with { or [)
- YAML detection (--- header)
- Markdown detection (combine multiple indicators)
- CSV detection (analyze structure)
- Plain text as default for unrecognized text

### Implement extension fallback system [Completed ✅]

Create comprehensive extension mapping:
- Map common file extensions to MIME types
- Use as last resort when content detection fails
- Log when falling back to extension
- Maintain compatibility with current behavior

### Add detection method priority logic [Completed ✅]

Implement the agreed priority order:
1. Binary signature detection (most reliable)
2. Content analysis for text formats
3. File extension as final fallback
- Add logging at each detection stage
- Return appropriate MIME type or raise exception

### Comments:
- Text detection needs to be careful to avoid false positives
- Extension fallback ensures graceful degradation
- **Implementation notes from Phase 2:**
  - Enhanced JSON detection with pattern matching and keyword checking
  - Improved YAML detection to avoid conflicts with Markdown
  - Added sophisticated Markdown scoring system (headers, lists, links, etc.)
  - Extended extension mapping to cover more file types (70+ extensions)
  - Fixed YAML/Markdown detection priority to avoid false positives
  - Added minimum content requirements for text detection
  - All text formats tested with edge cases

## PHASE 3: Integration with Existing Code [Completed ✅]

Replace libmagic usage throughout the codebase.

### Update identification module [Completed ✅]

Modify `/src/content_core/content/identification/__init__.py`:
- Import FileDetector
- Replace `magic.from_file()` call in `get_file_type()`
- Maintain async interface
- Remove magic import

### Update graph.py file type detection [Completed ✅]

Modify `/src/content_core/content/extraction/graph.py`:
- Replace `magic.from_file()` at line 62
- Import get_file_type from identification module
- Remove direct magic import
- Ensure error handling remains consistent

### Test integration thoroughly [Completed ✅]

Verify all extraction paths work:
- Test each supported file type through full pipeline
- Verify correct processor routing
- Check error messages for unsupported types
- Ensure no regression in functionality

### Comments:
- Must maintain exact same external behavior
- All existing code depending on MIME types should work unchanged
- **Implementation notes from Phase 3:**
  - Successfully replaced all libmagic usage with FileDetector
  - Integration was seamless - no changes needed to downstream processors
  - All file types correctly detected and routed to appropriate processors
  - Tested with PDF, DOCX, MP4, MP3, JSON, HTML, CSV, text files
  - Only test failure was unrelated (OpenAI API issue for MP3 transcription)
  - MIME types match exactly what libmagic returned

## PHASE 4: Cleanup and Final Validation [In Progress 🔄]

Remove dependencies and ensure production readiness.

### Remove libmagic from dependencies [Completed ✅]

Update `/pyproject.toml`:
- Remove `python-magic>=0.4.27`
- Remove `python-magic-bin==0.4.14` for Windows
- Update lock file with `uv sync`
- Verify clean installation works

**Implementation notes:**
- Successfully removed both python-magic dependencies from pyproject.toml
- Lock file updated with `uv sync`
- 2 packages uninstalled: python-magic and python-magic-bin

### Add comprehensive test suite [Not Started ⏳]

Create thorough tests:
- Unit tests for FileDetector methods
- Integration tests for full extraction pipeline
- Edge cases (empty files, malformed files)
- Cross-platform compatibility tests
- Performance benchmarks

### Documentation and release preparation [Not Started ⏳]

Final preparations:
- Update README if it mentions libmagic
- Add docstrings to all new code
- Update CHANGELOG
- Test installation on fresh environment
- Run full test suite: `make test`
- Build package: `uv build`

### Comments:
- This is a breaking change for anyone depending on libmagic behavior
- Consider adding migration guide if needed

## Key Technical Details

**Critical MIME Types** (must match exactly):
- `application/pdf` - PDF files
- `application/epub+zip` - EPUB files  
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - DOCX
- `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` - XLSX
- `application/vnd.openxmlformats-officedocument.presentationml.presentation` - PPTX
- `text/plain` - Text and Markdown files
- `text/html` - HTML files
- `text/csv` - CSV files
- `application/json` - JSON files
- `image/*` - Various image formats
- `video/*` - Video files (prefix matching)
- `audio/*` - Audio files (prefix matching)

**Implementation Constraints**:
- 512-byte buffer is sufficient (no deep file inspection needed)
- Performance is not critical (small load expected)
- Must raise `UnsupportedTypeException` for unknown types
- Maintain async interface for consistency
- Pure Python only (no C extensions)

**Risk Mitigation**:
- Extensive testing before removing libmagic
- Keep detection logic modular for easy updates
- Log detection decisions for debugging
- Consider feature flag for rollback if needed