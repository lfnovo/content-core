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
*   **Intelligent Processing:** Applies appropriate extraction techniques based on the source type.
*   **Content Cleaning (Optional):** Likely integrates with LLMs (via `prompter.py` and Jinja templates) to refine and clean the extracted content.
*   **Asynchronous:** Built with `asyncio` for efficient I/O operations.

## Getting Started

### Installation

Install Content Core using `pip`:

```bash
# Install the package
pip install content-core
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

if __name__ == "__main__":
    asyncio.run(main())
```

(See `src/content_core/notebooks/run.ipynb` for more detailed examples.)

## Configuration

Configuration settings (like API keys for external services, logging levels) can be managed through environment variables or `.env` files, loaded automatically via `python-dotenv`.

Example `.env`:

```plaintext
OPENAI_API_KEY=your-key-here
GOOGLE_API_KEY=your-key-here
```

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

## Contributing
Contributions are welcome! Please follow standard practices (fork, feature branch, pull request).

## License
This project is licensed under the MIT License - see the LICENSE file for details.
