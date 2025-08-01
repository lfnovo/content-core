# Content Core

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI version](https://badge.fury.io/py/content-core.svg)](https://badge.fury.io/py/content-core)
[![Downloads](https://pepy.tech/badge/content-core)](https://pepy.tech/project/content-core)
[![Downloads](https://pepy.tech/badge/content-core/month)](https://pepy.tech/project/content-core)
[![GitHub stars](https://img.shields.io/github/stars/lfnovo/content-core?style=social)](https://github.com/lfnovo/content-core)
[![GitHub forks](https://img.shields.io/github/forks/lfnovo/content-core?style=social)](https://github.com/lfnovo/content-core)
[![GitHub issues](https://img.shields.io/github/issues/lfnovo/content-core)](https://github.com/lfnovo/content-core/issues)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Content Core** is a powerful, AI-powered content extraction and processing platform that transforms any source into clean, structured content. Extract text from websites, transcribe videos, process documents, and generate AI summaries—all through a unified interface with multiple integration options.

## 🚀 What You Can Do

**Extract content from anywhere:**
- 📄 **Documents** - PDF, Word, PowerPoint, Excel, Markdown, HTML, EPUB
- 🎥 **Media** - Videos (MP4, AVI, MOV) with automatic transcription  
- 🎵 **Audio** - MP3, WAV, M4A with speech-to-text conversion
- 🌐 **Web** - Any URL with intelligent content extraction
- 🖼️ **Images** - JPG, PNG, TIFF with OCR text recognition
- 📦 **Archives** - ZIP, TAR, GZ with content analysis

**Process with AI:**
- ✨ **Clean & format** extracted content automatically
- 📝 **Generate summaries** with customizable styles (bullet points, executive summary, etc.)
- 🎯 **Context-aware processing** - explain to a child, technical summary, action items
- 🔄 **Smart engine selection** - automatically chooses the best extraction method

## 🛠️ Multiple Ways to Use

### 🖥️ Command Line (Zero Install)
```bash
# Extract content from any source
uvx --from "content-core" ccore https://example.com
uvx --from "content-core" ccore document.pdf

# Generate AI summaries  
uvx --from "content-core" csum video.mp4 --context "bullet points"
```

### 🤖 Claude Desktop Integration
One-click setup with Model Context Protocol (MCP) - extract content directly in Claude conversations.

### 🔍 Raycast Extension  
Smart auto-detection commands:
- **Extract Content** - Full interface with format options
- **Summarize Content** - 9 summary styles available
- **Quick Extract** - Instant clipboard extraction

### 🖱️ macOS Right-Click Integration
Right-click any file in Finder → Services → Extract or Summarize content instantly.

### 🐍 Python Library
```python
import content_core as cc

# Extract from any source
result = await cc.extract("https://example.com/article")
summary = await cc.summarize_content(result, context="explain to a child")
```

## ⚡ Key Features

*   **🎯 Intelligent Auto-Detection:** Automatically selects the best extraction method based on content type and available services
*   **🔧 Smart Engine Selection:** 
    * **URLs:** Firecrawl → Jina → BeautifulSoup fallback chain
    * **Documents:** Docling → Enhanced PyMuPDF → Simple extraction fallback  
    * **Media:** OpenAI Whisper transcription
    * **Images:** OCR with multiple engine support
*   **📊 Enhanced PDF Processing:** Advanced PyMuPDF engine with quality flags, table detection, and optional OCR for mathematical formulas
*   **🌍 Multiple Integrations:** CLI, Python library, MCP server, Raycast extension, macOS Services
*   **⚡ Zero-Install Options:** Use `uvx` for instant access without installation
*   **🧠 AI-Powered Processing:** LLM integration for content cleaning and summarization
*   **🔄 Asynchronous:** Built with `asyncio` for efficient processing
*   **🐍 Pure Python Implementation:** No system dependencies required - simplified installation across all platforms

## Getting Started

### Installation

Install Content Core using `pip` - **no system dependencies required!**

```bash
# Basic installation (PyMuPDF + BeautifulSoup/Jina extraction)
pip install content-core

# With enhanced document processing (adds Docling)
pip install content-core[docling]

# With MCP server support (now included by default)
pip install content-core

# Full installation (with enhanced document processing)
pip install content-core[docling]
```

> **Note:** Unlike many content extraction tools, Content Core uses pure Python implementations and doesn't require system libraries like libmagic. This ensures consistent, hassle-free installation across Windows, macOS, and Linux.

Alternatively, if you’re developing locally:

```bash
# Clone the repository
git clone https://github.com/lfnovo/content-core
cd content-core

# Install with uv
uv sync
```

### Command-Line Interface

Content Core provides three CLI commands for extracting, cleaning, and summarizing content: 
ccore, cclean, and csum. These commands support input from text, URLs, files, or piped data (e.g., via cat file | command).

**Zero-install usage with uvx:**
```bash
# Extract content
uvx --from "content-core" ccore https://example.com

# Clean content  
uvx --from "content-core" cclean "messy content"

# Summarize content
uvx --from "content-core" csum "long text" --context "bullet points"
```

#### ccore - Extract Content

Extracts content from text, URLs, or files, with optional formatting.
Usage:
```bash
ccore [-f|--format xml|json|text] [-d|--debug] [content]
```
Options:
- `-f`, `--format`: Output format (xml, json, or text). Default: text.
- `-d`, `--debug`: Enable debug logging.
- `content`: Input content (text, URL, or file path). If omitted, reads from stdin.

Examples:

```bash
# Extract from a URL as text
ccore https://example.com

# Extract from a file as JSON
ccore -f json document.pdf

# Extract from piped text as XML
echo "Sample text" | ccore --format xml
```

#### cclean - Clean Content
Cleans content by removing unnecessary formatting, spaces, or artifacts. Accepts text, JSON, XML input, URLs, or file paths.
Usage:

```bash
cclean [-d|--debug] [content]
```

Options:
- `-d`, `--debug`: Enable debug logging.
- `content`: Input content to clean (text, URL, file path, JSON, or XML). If omitted, reads from stdin.

Examples:

```bash
# Clean a text string
cclean "  messy   text   "

# Clean piped JSON
echo '{"content": "  messy   text   "}' | cclean

# Clean content from a URL
cclean https://example.com

# Clean a file’s content
cclean document.txt
```

### csum - Summarize Content

Summarizes content with an optional context to guide the summary style. Accepts text, JSON, XML input, URLs, or file paths.

Usage:

```bash
csum [--context "context text"] [-d|--debug] [content]
```

Options:
- `--context`: Context for summarization (e.g., "explain to a child"). Default: none.
- `-d`, `--debug`: Enable debug logging.
- `content`: Input content to summarize (text, URL, file path, JSON, or XML). If omitted, reads from stdin.

Examples:

```bash
# Summarize text
csum "AI is transforming industries."

# Summarize with context
csum --context "in bullet points" "AI is transforming industries."

# Summarize piped content
cat article.txt | csum --context "one sentence"

# Summarize content from URL
csum https://example.com

# Summarize a file's content
csum document.txt
```

## Quick Start

You can quickly integrate `content-core` into your Python projects to extract, clean, and summarize content from various sources.

```python
import content_core as cc

# Extract content from a URL, file, or text
result = await cc.extract("https://example.com/article")

# Clean messy content
cleaned_text = await cc.clean("...messy text with [brackets] and extra spaces...")

# Summarize content with optional context
summary = await cc.summarize_content("long article text", context="explain to a child")
```

## Documentation

For more information on how to use the Content Core library, including details on AI model configuration and customization, refer to our [Usage Documentation](docs/usage.md).

## MCP Server Integration

Content Core includes a Model Context Protocol (MCP) server that enables seamless integration with Claude Desktop and other MCP-compatible applications. The MCP server exposes Content Core's powerful extraction capabilities through a standardized protocol.

<a href="https://glama.ai/mcp/servers/@lfnovo/content-core">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@lfnovo/content-core/badge" />
</a>

### Quick Setup with Claude Desktop

```bash
# Install Content Core (MCP server included)
pip install content-core

# Or use directly with uvx (no installation required)
uvx --from "content-core" content-core-mcp
```

Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "content-core": {
      "command": "uvx",
      "args": [
        "--from",
        "content-core",
        "content-core-mcp"
      ]
    }
  }
}
```

For detailed setup instructions, configuration options, and usage examples, see our [MCP Documentation](docs/mcp.md).

## Enhanced PDF Processing

Content Core features an optimized PyMuPDF extraction engine with significant improvements for scientific documents and complex PDFs.

### Key Improvements

- **🔬 Mathematical Formula Extraction**: Enhanced quality flags eliminate `<!-- formula-not-decoded -->` placeholders
- **📊 Automatic Table Detection**: Tables converted to markdown format for LLM consumption
- **🔧 Quality Text Rendering**: Better ligature, whitespace, and image-text integration
- **⚡ Optional OCR Enhancement**: Selective OCR for formula-heavy pages (requires Tesseract)

### Configuration for Scientific Documents

For documents with heavy mathematical content, enable OCR enhancement:

```yaml
# In cc_config.yaml
extraction:
  pymupdf:
    enable_formula_ocr: true      # Enable OCR for formula-heavy pages
    formula_threshold: 3          # Min formulas per page to trigger OCR
    ocr_fallback: true           # Graceful fallback if OCR fails
```

```python
# Runtime configuration
from content_core.config import set_pymupdf_ocr_enabled
set_pymupdf_ocr_enabled(True)
```

### Requirements for OCR Enhancement

```bash
# Install Tesseract OCR (optional, for formula enhancement)
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
```

**Note**: OCR is optional - you get improved PDF extraction automatically without any additional setup.

## macOS Services Integration

Content Core provides powerful right-click integration with macOS Finder, allowing you to extract and summarize content from any file without installation. Choose between clipboard or TextEdit output for maximum flexibility.

### Available Services

Create **4 convenient services** for different workflows:

- **Extract Content → Clipboard** - Quick copy for immediate pasting
- **Extract Content → TextEdit** - Review before using  
- **Summarize Content → Clipboard** - Quick summary copying
- **Summarize Content → TextEdit** - Formatted summary with headers

### Quick Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create services manually** using Automator (5 minutes setup)

### Usage

**Right-click any supported file** in Finder → **Services** → Choose your option:

- **PDFs, Word docs** - Instant text extraction
- **Videos, audio files** - Automatic transcription  
- **Images** - OCR text recognition
- **Web content** - Clean text extraction
- **Multiple files** - Batch processing support

### Features

- **Zero-install processing**: Uses `uvx` for isolated execution
- **Multiple output options**: Clipboard or TextEdit display
- **System notifications**: Visual feedback on completion
- **Wide format support**: 20+ file types supported
- **Batch processing**: Handle multiple files at once
- **Keyboard shortcuts**: Assignable hotkeys for power users

For complete setup instructions with copy-paste scripts, see [macOS Services Documentation](docs/macos.md).

## Raycast Extension

Content Core provides a powerful Raycast extension with smart auto-detection that handles both URLs and file paths seamlessly. Extract and summarize content directly from your Raycast interface without switching applications.

### Quick Setup

**From Raycast Store** (coming soon):
1. Open Raycast and search for "Content Core"
2. Install the extension by `luis_novo`
3. Configure API keys in preferences

**Manual Installation**:
1. Download the extension from the repository
2. Open Raycast → "Import Extension"
3. Select the `raycast-content-core` folder

### Commands

**🔍 Extract Content** - Smart URL/file detection with full interface
- Auto-detects URLs vs file paths in real-time
- Multiple output formats (Text, JSON, XML)
- Drag & drop support for files
- Rich results view with metadata

**📝 Summarize Content** - AI-powered summaries with customizable styles  
- 9 different summary styles (bullet points, executive summary, etc.)
- Auto-detects source type with visual feedback
- One-click snippet creation and quicklinks

**⚡ Quick Extract** - Instant extraction to clipboard
- Type → Tab → Paste source → Enter
- No UI, works directly from command bar
- Perfect for quick workflows

### Features

- **Smart Auto-Detection**: Instantly recognizes URLs vs file paths
- **Zero Installation**: Uses `uvx` for Content Core execution
- **Rich Integration**: Keyboard shortcuts, clipboard actions, Raycast snippets
- **All File Types**: Documents, videos, audio, images, archives
- **Visual Feedback**: Real-time type detection with icons

For detailed setup, configuration, and usage examples, see [Raycast Extension Documentation](docs/raycast.md).

## Using with Langchain

For users integrating with the [Langchain](https://python.langchain.com/) framework, `content-core` exposes a set of compatible tools. These tools, located in the `src/content_core/tools` directory, allow you to leverage `content-core` extraction, cleaning, and summarization capabilities directly within your Langchain agents and chains.

You can import and use these tools like any other Langchain tool. For example:

```python
from content_core.tools import extract_content_tool, cleanup_content_tool, summarize_content_tool
from langchain.agents import initialize_agent, AgentType

tools = [extract_content_tool, cleanup_content_tool, summarize_content_tool]
agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)
agent.run("Extract the content from https://example.com and then summarize it.") 
```

Refer to the source code in `src/content_core/tools` for specific tool implementations and usage details.

## Basic Usage

The core functionality revolves around the extract_content function.

```python
import asyncio
from content_core.extraction import extract_content

async def main():
    # Extract from raw text
    text_data = await extract_content({"content": "This is my sample text content."})
    print(text_data)

    # Extract from a URL (uses 'auto' engine by default)
    url_data = await extract_content({"url": "https://www.example.com"})
    print(url_data)

    # Extract from a local video file (gets transcript, engine='auto' by default)
    video_data = await extract_content({"file_path": "path/to/your/video.mp4"})
    print(video_data)

    # Extract from a local markdown file (engine='auto' by default)
    md_data = await extract_content({"file_path": "path/to/your/document.md"})
    print(md_data)

    # Per-execution override with Docling for documents
    doc_data = await extract_content({
        "file_path": "path/to/your/document.pdf",
        "document_engine": "docling",
        "output_format": "html"
    })
    
    # Per-execution override with Firecrawl for URLs
    url_data = await extract_content({
        "url": "https://www.example.com",
        "url_engine": "firecrawl"
    })
    print(doc_data)

if __name__ == "__main__":
    asyncio.run(main())
```

(See `src/content_core/notebooks/run.ipynb` for more detailed examples.)

## Docling Integration

Content Core supports an optional Docling-based extraction engine for rich document formats (PDF, DOCX, PPTX, XLSX, Markdown, AsciiDoc, HTML, CSV, Images).


### Enabling Docling

Docling is not the default engine when parsing documents. If you don't want to use it, you need to set engine to "simple". 

#### Via configuration file

In your `cc_config.yaml` or custom config, set:
```yaml
extraction:
  document_engine: docling  # 'auto' (default), 'simple', or 'docling'
  url_engine: auto          # 'auto' (default), 'simple', 'firecrawl', or 'jina'
  docling:
    output_format: markdown  # markdown | html | json
```

#### Programmatically in Python

```python
from content_core.config import set_document_engine, set_url_engine, set_docling_output_format

# switch document engine to Docling
set_document_engine("docling")

# switch URL engine to Firecrawl
set_url_engine("firecrawl")

# choose output format: 'markdown', 'html', or 'json'
set_docling_output_format("html")

# now use ccore.extract or ccore.ccore
result = await cc.extract("document.pdf")
```

## Configuration

Configuration settings (like API keys for external services, logging levels) can be managed through environment variables or `.env` files, loaded automatically via `python-dotenv`.

Example `.env`:

```plaintext
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here

# Engine Selection (optional)
CCORE_DOCUMENT_ENGINE=auto  # auto, simple, docling
CCORE_URL_ENGINE=auto       # auto, simple, firecrawl, jina
```

### Engine Selection via Environment Variables

For deployment scenarios like MCP servers or Raycast extensions, you can override the extraction engines using environment variables:

- **`CCORE_DOCUMENT_ENGINE`**: Force document engine (`auto`, `simple`, `docling`)
- **`CCORE_URL_ENGINE`**: Force URL engine (`auto`, `simple`, `firecrawl`, `jina`)

These variables take precedence over config file settings and provide explicit control for different deployment scenarios.

### Custom Prompt Templates

Content Core allows you to define custom prompt templates for content processing. By default, the library uses built-in prompts located in the `prompts` directory. However, you can create your own prompt templates and store them in a dedicated directory. To specify the location of your custom prompts, set the `PROMPT_PATH` environment variable in your `.env` file or system environment.

Example `.env` with custom prompt path:

```plaintext
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
PROMPT_PATH=/path/to/your/custom/prompts
```

When a prompt template is requested, Content Core will first look in the custom directory specified by `PROMPT_PATH` (if set and exists). If the template is not found there, it will fall back to the default built-in prompts. This allows you to override specific prompts while still using the default ones for others.

## Development

To set up a development environment:

```bash
# Clone the repository
git clone <repository-url>
cd content-core

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync --group dev

# Run tests
make test

# Lint code
make lint

# See all commands
make help
```

## License

This project is licensed under the [MIT License](LICENSE). See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for more details on how to get started.
