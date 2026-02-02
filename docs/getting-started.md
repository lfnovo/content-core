# Getting Started

This guide helps you get up and running with Content Core quickly.

## Installation

### Basic Installation

```bash
pip install content-core
```

This installs Content Core with the default Docling engine (MIT license).

### Optional Dependencies

```bash
# Faster PDF extraction (AGPL-3.0 license)
pip install content-core[pymupdf]

# VLM-powered extraction for complex documents
pip install content-core[docling-vlm]

# Apple Silicon optimized VLM
pip install content-core[docling-mlx]

# Local browser-based URL extraction
pip install content-core[crawl4ai]
python -m playwright install --with-deps

# Full installation
pip install content-core[pymupdf,docling-vlm,crawl4ai]
```

## Quick Start

### Command Line

```bash
# Extract content from URL
ccore https://example.com

# Extract from file
ccore document.pdf

# Clean content
cclean "  messy   text   "

# Summarize
csum article.txt --context "bullet points"
```

### Python

```python
import content_core as cc

# Extract content
result = await cc.extract("https://example.com")
print(result.content)

# Extract from file
result = await cc.extract("document.pdf")

# Clean messy content
cleaned = await cc.clean("  messy   text   ")

# Summarize with context
summary = await cc.summarize_content(
    "Long article text here...",
    context="explain to a child"
)
```

## Configuration

### API Keys

Content Core uses LLMs for cleaning and summarization. Set your API key:

```bash
export OPENAI_API_KEY=your-key
```

### Optional API Keys

```bash
# For Firecrawl URL extraction
export FIRECRAWL_API_KEY=your-key

# For Jina URL extraction (higher rate limits)
export JINA_API_KEY=your-key
```

### Engine Selection

```bash
# Document engine
export CCORE_DOCUMENT_ENGINE=docling  # auto, simple, docling, docling-vlm

# URL engine
export CCORE_URL_ENGINE=auto  # auto, simple, firecrawl, jina, crawl4ai
```

## Common Use Cases

### Extract from URL

```python
import content_core as cc

result = await cc.extract("https://news.example.com/article")
print(result.content)
```

### Extract from PDF

```python
import content_core as cc

result = await cc.extract("report.pdf")
print(result.content)
```

### Transcribe Video

```python
import content_core as cc

result = await cc.extract("interview.mp4")
print(result.content)  # Full transcript
```

### Summarize Content

```python
import content_core as cc

# Extract first
result = await cc.extract("long_document.pdf")

# Then summarize
summary = await cc.summarize_content(
    result.content,
    context="executive summary in 3 bullet points"
)
```

### Batch Processing

```python
import content_core as cc
import asyncio

files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]

async def process_files():
    results = []
    for file in files:
        result = await cc.extract(file)
        results.append(result)
    return results

results = asyncio.run(process_files())
```

## Next Steps

- [Configuration Guide](configuration.md) - All configuration options
- [CLI Reference](cli.md) - Command-line tools
- [Engine Overview](engines/overview.md) - Choose the right engine
- [Benchmarks](benchmarks/pdf-benchmark.md) - Performance comparisons
