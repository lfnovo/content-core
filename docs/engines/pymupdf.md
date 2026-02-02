# PyMuPDF Engine

PyMuPDF (via `pymupdf4llm`) provides fast, lightweight PDF extraction with enhanced quality flags.

## License

**AGPL-3.0** - This is a copyleft license. If you use PyMuPDF in your application:

1. **Open Source Option:** Release your application under AGPL-3.0
2. **Commercial License:** Purchase from [Artifex](https://artifex.com/licensing)

For MIT-only extraction, use the default `docling` engine instead.

## Installation

```bash
# Install Content Core with PyMuPDF support
pip install content-core[pymupdf]
```

## Configuration

### Environment Variables

```bash
export CCORE_DOCUMENT_ENGINE=simple  # Use PyMuPDF engine
```

### YAML Configuration

```yaml
extraction:
  document_engine: simple  # Uses PyMuPDF when available
  pymupdf:
    enable_formula_ocr: false    # Enable OCR for formula-heavy pages
    formula_threshold: 3         # Min formulas per page to trigger OCR
    ocr_fallback: true          # Graceful fallback if OCR fails
```

### Python

```python
from content_core.config import set_document_engine, set_pymupdf_ocr_enabled

set_document_engine("simple")
set_pymupdf_ocr_enabled(True)  # Enable OCR for scientific docs
```

## Features

### Quality Flags

PyMuPDF automatically applies quality flags for better text extraction:

- `TEXT_PRESERVE_LIGATURES` - Better character rendering
- `TEXT_PRESERVE_WHITESPACE` - Improved spacing
- `TEXT_PRESERVE_IMAGES` - Better integration of image-embedded text

### Table Detection

Tables are automatically detected and converted to markdown format:

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
```

### Mathematical Formula Enhancement

Eliminates `<!-- formula-not-decoded -->` placeholders by properly extracting mathematical symbols (∂, ∇, ρ, etc.).

### Optional OCR Enhancement

For scientific documents with complex formulas, enable selective OCR:

```python
from content_core.config import set_pymupdf_ocr_enabled, set_pymupdf_formula_threshold

set_pymupdf_ocr_enabled(True)
set_pymupdf_formula_threshold(2)  # Lower threshold for math-heavy docs
```

**Requirements:**
```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
```

## Performance

| Metric | Value |
|--------|-------|
| Speed | ~0.1-0.5s per page |
| Memory | ~10-50MB |
| Quality | Good for simple documents |

**Note:** OCR is ~1000x slower than standard extraction but only triggers on formula-heavy pages.

## When to Use

**Use PyMuPDF when:**
- Speed is priority over perfect quality
- Documents are simple (no complex layouts)
- You can comply with AGPL-3.0 or have commercial license

**Don't use when:**
- You need MIT-only licensing (use `docling`)
- Documents have complex layouts (use `docling-vlm` or `marker`)
- Tables are critical (use `docling` for better table extraction)

## Supported Formats

- PDF files
- EPUB files

## Gotchas

1. **License:** AGPL-3.0 requires open-source or commercial license
2. **Optional dependency:** Not installed by default
3. **Table extraction:** Basic compared to Docling
4. **Complex layouts:** May struggle with multi-column or complex documents

## Checking Availability

```python
from content_core.processors.pdf import PYMUPDF_AVAILABLE, PYMUPDF4LLM_AVAILABLE

if PYMUPDF_AVAILABLE:
    print("PyMuPDF is available")
if PYMUPDF4LLM_AVAILABLE:
    print("pymupdf4llm is available")
```
