# Content Core

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/content-core.svg)](https://badge.fury.io/py/content-core)
[![Downloads](https://pepy.tech/badge/content-core)](https://pepy.tech/project/content-core)

**Content Core** is an AI-powered content extraction library that transforms any source into clean, structured content. Extract text from websites, transcribe videos, process documents, and generate AI summaries.

## Features

- **Documents** - PDF, Word, PowerPoint, Excel, Markdown, HTML, EPUB
- **Media** - Videos and audio with automatic transcription
- **Web** - URLs with intelligent content extraction
- **Images** - OCR text recognition
- **AI Processing** - Clean, format, and summarize with LLMs

## Installation

```bash
# Basic installation (MIT license)
pip install content-core

# With faster PDF extraction (AGPL-3.0)
pip install content-core[pymupdf]

# With VLM-powered extraction
pip install content-core[docling-vlm]

# With local browser-based URL extraction
pip install content-core[crawl4ai]
```

## Quick Start

### Command Line

```bash
# Extract content
ccore https://example.com
ccore document.pdf

# Summarize
csum video.mp4 --context "bullet points"

# Zero-install with uvx
uvx --from "content-core" ccore https://example.com
```

### Python

```python
import content_core as cc

# Extract from any source
result = await cc.extract("https://example.com/article")
result = await cc.extract("document.pdf")

# Summarize
summary = await cc.summarize_content(result, context="explain to a child")

# Clean messy content
cleaned = await cc.clean("...messy text...")
```

## Integrations

| Integration | Description |
|-------------|-------------|
| [CLI](docs/cli.md) | Command-line tools (ccore, cclean, csum) |
| [MCP Server](docs/integrations/mcp.md) | Claude Desktop integration |
| [Raycast](docs/integrations/raycast.md) | Raycast extension |
| [macOS Services](docs/integrations/macos.md) | Right-click in Finder |
| [LangChain](docs/integrations/langchain.md) | Agent tools |

## Extraction Engines

Content Core supports multiple extraction engines with automatic selection:

| Engine | License | Best For |
|--------|---------|----------|
| [docling](docs/engines/docling.md) (default) | MIT | Most documents |
| [pymupdf](docs/engines/pymupdf.md) | AGPL-3.0 | Fast PDF extraction |
| [docling-vlm](docs/engines/docling-vlm.md) | MIT | Complex layouts |
| [marker](docs/engines/marker.md) | GPL-3.0 | Scientific papers |

See [Engine Overview](docs/engines/overview.md) and [Benchmarks](docs/benchmarks/pdf-benchmark.md) for detailed comparisons.

## Configuration

```bash
# Set extraction engines
export CCORE_DOCUMENT_ENGINE=docling  # auto, simple, docling, docling-vlm
export CCORE_URL_ENGINE=auto          # auto, simple, firecrawl, jina, crawl4ai

# API keys
export OPENAI_API_KEY=your-key
export FIRECRAWL_API_KEY=your-key     # Optional, for Firecrawl
```

See [Configuration Guide](docs/configuration.md) for all options.

## Documentation

- [Getting Started](docs/getting-started.md)
- [Configuration](docs/configuration.md)
- [CLI Reference](docs/cli.md)
- [Engines](docs/engines/overview.md)
- [Benchmarks](docs/benchmarks/pdf-benchmark.md)
- [Integrations](docs/integrations/)

## License

MIT License. See [LICENSE](LICENSE) for details.

**Optional Dependencies:**

| Package | License | Installation |
|---------|---------|--------------|
| docling | MIT | Included |
| pymupdf | AGPL-3.0 | `pip install content-core[pymupdf]` |
| marker | GPL-3.0 | `pip install marker-pdf` |

For commercial use with AGPL/GPL dependencies, see their respective licensing options.

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).
