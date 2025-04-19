# Content Core

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Content Core** is a versatile Python library designed to extract and process content from various sources, providing a unified interface for handling text, web pages, and local files.

## Overview

The primary goal of Content Core is to simplify the process of ingesting content from diverse origins. Whether you have raw text, a URL pointing to an article, or a local file like a video or markdown document, Content Core aims to extract the meaningful content for further use.

## Key Features

*   **Multi-Source Extraction:** Handles content from:
    *   Direct text strings.
    *   Web URLs (using robust extraction methods).
    *   Local files (including automatic transcription for video/audio files and parsing for text-based formats).
*   **Intelligent Processing:** Applies appropriate extraction techniques based on the source type. See the [Processors Documentation](./docs/processors.md) for detailed information on how different content types are handled.
*   **Content Cleaning (Optional):** Likely integrates with LLMs (via `prompter.py` and Jinja templates) to refine and clean the extracted content.
*   **Asynchronous:** Built with `asyncio` for efficient I/O operations.

## Getting Started

### Installation

Install Content Core using `pip`:

```bash
# Install the package (without Docling)
pip install content-core
# Install with Docling support
pip install content-core[docling]
```

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

    # Extract from a URL
    url_data = await extract_content({"url": "https://www.example.com"})
    print(url_data)

    # Extract from a local video file (gets transcript)
    video_data = await extract_content({"file_path": "path/to/your/video.mp4"})
    print(video_data)

    # Extract from a local markdown file
    md_data = await extract_content({"file_path": "path/to/your/document.md"})
    print(md_data)

    # Per-execution override with Docling
    doc_data = await extract_content({
        "file_path": "path/to/your/document.pdf",
        "engine": "docling",
        "output_format": "html"
    })
    print(doc_data)

if __name__ == "__main__":
    asyncio.run(main())
```

(See `src/content_core/notebooks/run.ipynb` for more detailed examples.)

## Docling Integration

Content Core supports an optional Docling-based extraction engine for rich document formats (PDF, DOCX, PPTX, XLSX, Markdown, AsciiDoc, HTML, CSV, Images).

### Installation

```bash
# Install with Docling support
pip install content-core[docling]
```

### Enabling Docling

#### Via configuration file

In your `cc_config.yaml` or custom config, set:
```yaml
extraction:
  engine: docling       # 'legacy' (default) or 'docling'
  docling:
    output_format: markdown  # markdown | html | json
```

#### Programmatically in Python

```python
from content_core.config import set_extraction_engine, set_docling_output_format

# switch engine to Docling
set_extraction_engine("docling")

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
```

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
