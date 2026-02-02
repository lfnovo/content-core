# Docling Engine

Docling is the default extraction engine in Content Core. It provides high-quality document understanding with MIT licensing.

## License

**MIT** - Commercial-friendly, no restrictions on use.

## Installation

```bash
# Docling is included by default
pip install content-core
```

## Configuration

### Environment Variables

```bash
export CCORE_DOCUMENT_ENGINE=docling
export CCORE_DOCLING_OUTPUT_FORMAT=markdown  # markdown, html, or json
```

### YAML Configuration

```yaml
extraction:
  document_engine: docling
  docling:
    output_format: markdown  # markdown | html | json
    options:
      do_picture_description: false
      picture_description_model: granite  # smolvlm | granite
      images_scale: 2.0
```

### Python

```python
from content_core.config import set_document_engine, set_docling_output_format

set_document_engine("docling")
set_docling_output_format("html")
```

## Features

### Rich Document Parsing

Docling understands document structure including:
- Headers and sections
- Tables with proper structure
- Lists (numbered and bulleted)
- Code blocks
- Images and figures

### Multiple Output Formats

```python
# Markdown (default)
result = await cc.extract({
    "file_path": "doc.pdf",
    "output_format": "markdown"
})

# HTML
result = await cc.extract({
    "file_path": "doc.pdf",
    "output_format": "html"
})

# JSON (document model)
result = await cc.extract({
    "file_path": "doc.pdf",
    "output_format": "json"
})
```

### Picture Description (VLM-based)

Enable automatic image captioning using Vision Language Models:

```bash
export CCORE_DOCLING_DO_PICTURE_DESCRIPTION=true
export CCORE_DOCLING_PICTURE_MODEL=granite  # or smolvlm
```

**Available Models:**

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| smolvlm | 256M | ~30s/doc | Good |
| granite | 2B | ~100s/doc | Better |

**Important Notes:**
- Uses CPU for inference (MPS/Apple Silicon GPU produces incorrect output)
- Descriptions stored in `pic.meta.description.text`
- Markdown export shows `<!-- image -->` placeholder

## Performance

| Metric | Value |
|--------|-------|
| Speed | ~5-15s per document |
| Memory | ~100-200MB |
| Quality | High for structured documents |

## Supported Formats

- PDF
- DOCX, XLSX, PPTX
- HTML, XML
- Markdown, AsciiDoc
- CSV
- Images (PNG, JPEG, TIFF, BMP)

## When to Use

**Use Docling when:**
- You need MIT licensing
- Documents have tables and structure
- You need multiple output formats
- You want the default, recommended engine

**Don't use when:**
- Documents have very complex layouts (use `docling-vlm`)
- You need the fastest possible extraction (use `pymupdf4llm`)

## Gotchas

1. **Picture description on CPU:** MPS/GPU produces incorrect output with SmolVLM
2. **Memory usage:** Can be high for large documents
3. **First run:** Model downloads on first use

## Checking Availability

```python
from content_core.processors.docling import DOCLING_AVAILABLE

if DOCLING_AVAILABLE:
    print("Docling is available")
```

## Comparison with Other Engines

| Feature | Docling | PyMuPDF | Marker |
|---------|---------|---------|--------|
| License | MIT | AGPL-3.0 | GPL-3.0 |
| Tables | Excellent | Basic | Good |
| Speed | Medium | Fast | Slow |
| Complex Layouts | Good | Poor | Excellent |
| Output Formats | 3 | 1 | 1 |
