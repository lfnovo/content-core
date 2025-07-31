# OSS-216: Remove libmagic Dependency - Context

## Why This Is Being Built

- **Deployment Friction**: libmagic requires OS-level installation which creates deployment problems
- **Cross-Platform Issues**: Binary dependency causes installation problems across Windows, macOS, and Linux
- **Simplification**: Removing system dependencies makes the package easier to install and use
- **Maintain Functionality**: Need to keep intelligent file detection without external dependencies

## Expected Outcome

Replace libmagic with a pure Python implementation that:
- Detects file types using magic bytes/file signatures (first 512 bytes)
- Maintains the current routing behavior to appropriate content processors
- Works across all platforms without OS-level dependencies
- Keeps the same error handling (UnsupportedTypeException for unsupported types)

## Implementation Approach

1. **File Signature Detection System**:
   - Build comprehensive mapping of file signatures to MIME types
   - Read first 512 bytes to identify format by magic bytes
   - Special handling for Office formats (DOCX, XLSX, PPTX) which are ZIP-based
   - Content structure analysis for text formats (HTML, JSON, XML)

2. **Detection Priority** (as discussed):
   - Primary: File signature/magic bytes detection
   - Secondary: Content analysis for text formats
   - Tertiary: File extension as final fallback
   - If file extension and content disagree, prioritize content analysis

3. **Replace Current Usage**:
   - Remove imports of `magic` library
   - Replace `magic.from_file()` calls in:
     - `/src/content_core/content/identification/__init__.py`
     - `/src/content_core/content/extraction/graph.py`
   - Remove dependencies from `pyproject.toml`

## Testing Approach

- Comprehensive testing will be handled later
- Focus on maintaining existing functionality
- Ensure all currently supported file types continue to work

## Dependencies

No new dependencies - implementation should be pure Python using only standard library.

## Constraints

- 512 bytes buffer is sufficient (no need for deep ZIP inspection)
- Performance is not a concern (load is small)
- Maintain current error behavior (raise UnsupportedTypeException)
- MIME type strings can be adjusted as long as routing works correctly