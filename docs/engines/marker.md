# Marker Engine

Marker uses deep learning models to convert PDFs to high-quality markdown, excelling at complex documents and scientific papers.

## License

**GPL-3.0** - This is a copyleft license. If you use Marker in your application:

1. **Open Source Option:** Release your application under GPL-3.0
2. **Commercial License:** Contact the Marker team for licensing options

For MIT-only extraction, use the default `docling` engine instead.

## Installation

```bash
# Install Marker
pip install marker-pdf
```

**Note:** Marker is NOT included in Content Core's optional dependencies due to its GPL license. Install it separately if needed.

## Configuration

Marker is used through the benchmark system or by importing directly:

```python
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

artifact_dict = create_model_dict()
converter = PdfConverter(artifact_dict=artifact_dict)
result = converter("document.pdf")
markdown = result.markdown
```

## Features

### Deep Learning Extraction

Marker uses trained models for:
- Layout detection
- Table recognition
- Formula extraction
- Reading order detection

### High-Quality Output

- Excellent mathematical formula support
- Accurate table extraction
- Proper reading order for complex layouts
- Good handling of multi-column documents

## Performance

| Metric | Value |
|--------|-------|
| Speed | ~30-120s per document |
| Memory | ~2-4GB |
| Quality | Excellent for complex documents |

**First Run:** Downloads ~2-5GB of models.

## System Requirements

### macOS

```bash
# May need to set library path for some dependencies
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

### Linux

No special requirements beyond Python dependencies.

### Windows

May require Visual C++ Build Tools for some dependencies.

## When to Use

**Use Marker when:**
- Documents have complex mathematical formulas
- Scientific papers with figures and equations
- Multi-column layouts
- You need the highest quality extraction
- You can comply with GPL-3.0

**Don't use when:**
- You need MIT licensing (use `docling`)
- Speed is priority (use `pymupdf4llm`)
- Simple text documents

## Supported Formats

- PDF files only

## Gotchas

1. **License:** GPL-3.0 requires open-source or commercial license
2. **Large models:** Downloads 2-5GB on first run
3. **Slow:** Deep learning inference is computationally expensive
4. **Memory:** Requires significant RAM (2-4GB)
5. **macOS:** May need `DYLD_LIBRARY_PATH` set
6. **Not in Content Core extras:** Must be installed separately

## Comparison with Other Engines

| Feature | Marker | Docling | PyMuPDF |
|---------|--------|---------|---------|
| License | GPL-3.0 | MIT | AGPL-3.0 |
| Speed | Slow | Medium | Fast |
| Formulas | Excellent | Good | Basic |
| Tables | Good | Excellent | Basic |
| Complex Layouts | Excellent | Good | Poor |
| Model Size | ~2-5GB | ~100MB | None |

## Benchmark Results

See [PDF Benchmark](../benchmarks/pdf-benchmark.md) for detailed comparisons.
