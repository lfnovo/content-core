# Document Extraction Engines

Content Core supports multiple extraction engines for documents and URLs. This guide helps you choose the right engine for your needs.

## Quick Comparison

### Document Engines (PDF, DOCX, etc.)

| Engine | License | Speed | Quality | Best For |
|--------|---------|-------|---------|----------|
| **docling** (default) | MIT | Medium | High | Most documents, tables, structure |
| **pymupdf4llm** | AGPL-3.0 | Fast | Good | Simple PDFs, speed priority |
| **marker** | GPL-3.0 | Slow | Excellent | Complex layouts, scientific papers |
| **docling-vlm** | MIT | Slow | Excellent | Complex layouts, images, diagrams |

### URL Engines

| Engine | License | API Key Required | Best For |
|--------|---------|------------------|----------|
| **firecrawl** | - | Yes | JavaScript-heavy sites, best quality |
| **jina** | - | Optional | General use, good fallback |
| **crawl4ai** | Apache-2.0 | No | Privacy-first, local processing |
| **bs4** (simple) | MIT | No | Simple pages, fast |

## Engine Selection

### Automatic Selection (Recommended)

By default, Content Core uses `auto` engine selection:

```python
import content_core as cc

# Auto-selects best available engine
result = await cc.extract("document.pdf")
result = await cc.extract("https://example.com")
```

**Document fallback order:** docling → pymupdf4llm → simple
**URL fallback order:** firecrawl (if API key) → jina → crawl4ai → bs4

### Manual Selection

```python
# Force specific document engine
result = await cc.extract({
    "file_path": "document.pdf",
    "document_engine": "docling"
})

# Force specific URL engine
result = await cc.extract({
    "url": "https://example.com",
    "url_engine": "firecrawl"
})
```

### Environment Variables

```bash
# Set default document engine
export CCORE_DOCUMENT_ENGINE=docling  # auto, simple, docling, docling-vlm

# Set default URL engine
export CCORE_URL_ENGINE=auto  # auto, simple, firecrawl, jina, crawl4ai
```

## When to Use Each Engine

### docling (Default)
- **Best for:** Most documents, especially those with tables and structure
- **License:** MIT (commercial-friendly)
- **Install:** Included by default

```bash
pip install content-core
```

### pymupdf4llm
- **Best for:** Fast extraction when speed is priority
- **License:** AGPL-3.0 (requires open-source or commercial license)
- **Install:** Optional

```bash
pip install content-core[pymupdf]
```

### marker
- **Best for:** Complex scientific papers, mathematical formulas
- **License:** GPL-3.0 (requires open-source or commercial license)
- **Gotchas:** Large model downloads (~2-5GB), slow first run

```bash
pip install marker-pdf
```

### docling-vlm
- **Best for:** Documents with complex layouts, charts, diagrams
- **License:** MIT
- **Gotchas:** Requires GPU for reasonable speed

```bash
pip install content-core[docling-vlm]  # transformers backend
pip install content-core[docling-mlx]  # Apple Silicon optimized
```

## Detailed Engine Documentation

- [PyMuPDF Engine](./pymupdf.md) - Fast extraction with AGPL-3.0 license
- [Docling Engine](./docling.md) - MIT-licensed document understanding
- [Docling VLM Engine](./docling-vlm.md) - Vision-language model extraction
- [Marker Engine](./marker.md) - Deep learning PDF extraction
- [URL Engines](./url-engines.md) - Web content extraction
- [Audio/Video](./audio-video.md) - Media transcription

## Benchmarks

See our [benchmark results](../benchmarks/pdf-benchmark.md) for detailed performance comparisons.
