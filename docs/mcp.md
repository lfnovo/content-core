# MCP Server Documentation

Content Core includes a Model Context Protocol (MCP) server that provides powerful content extraction capabilities to Claude Desktop and other MCP-compatible applications. The server exposes a single, easy-to-use tool that can extract content from URLs and files using Content Core's advanced extraction engines.

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open standard that enables AI applications to securely connect to external data sources and tools. Content Core's MCP server allows Claude Desktop to directly extract content from various sources, making it easy to process web pages, documents, videos, and other media within your conversations.

## Features

- **Single tool interface**: `extract_content` function accepts either URLs or file paths
- **Auto engine selection**: Uses Content Core's intelligent 'auto' engine for optimal extraction
- **Rich metadata**: Returns detailed information about extraction process and content
- **Structured JSON responses**: Consistent format with success/error handling
- **Wide format support**: Handles web pages, PDFs, Word docs, videos, audio files, and more
- **Zero-install option**: Run MCP server and CLI tools with `uvx` without local installation

## Installation

### Option 1: Install with pip (Recommended for local development)

```bash
# Install Content Core (MCP server included by default)
pip install content-core

# The content-core-mcp command becomes available
content-core-mcp
```

### Option 2: Use with uvx (Recommended for production)

```bash
# Run MCP server directly without installation
uvx --from "content-core" content-core-mcp

# Also works for CLI tools
uvx --from "content-core" ccore https://example.com
uvx --from "content-core" cclean "messy text"
uvx --from "content-core" csum "long content" --context "bullet points"
```

## Claude Desktop Setup

### Configuration

Add Content Core to your Claude Desktop configuration file:

**Location of config file:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Production Configuration (using uvx)

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

### Local Development Configuration

```json
{
  "mcpServers": {
    "content-core": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/content-core",
        "run",
        "content-core-mcp"
      ]
    }
  }
}
```

### With Environment Variables

For optimal functionality, you'll need to configure API keys. Here's what each key does:

**Required:**
- `OPENAI_API_KEY` - **Required for audio/video transcription and content cleaning**

**Optional (but recommended):**
- `FIRECRAWL_API_KEY` - **Improved web crawling and content extraction from URLs**
- `JINA_API_KEY` - **Alternative web crawling service (fallback when Firecrawl unavailable)**

```json
{
  "mcpServers": {
    "content-core": {
      "command": "uvx",
      "args": [
        "--from",
        "content-core",
        "content-core-mcp"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-your-openai-key-here",
        "FIRECRAWL_API_KEY": "fc-your-firecrawl-key-here",
        "JINA_API_KEY": "jina-your-jina-key-here"
      }
    }
  }
}
```

**Note:** Without `OPENAI_API_KEY`, you won't be able to:
- Transcribe audio or video files
- Use AI-powered content cleaning and summarization features

Without the web crawling API keys, Content Core will fall back to basic BeautifulSoup extraction for URLs, which may be less reliable for complex websites.

## Usage

After setting up the MCP server, you can use it directly in Claude Desktop conversations. The server provides one main tool:

### extract_content

Extract content from URLs or files using Content Core's auto engine.

**Parameters:**
- `url` (optional): URL to extract content from
- `file_path` (optional): Local file path to extract content from

**Note**: Exactly one parameter must be provided (either `url` OR `file_path`, not both).

## Examples

### Extracting from URLs

**Prompt in Claude Desktop:**
```
Please extract the content from https://example.com/article
```

**What happens:**
Claude will use the MCP server to extract the article content, including the title, main text, and metadata.

### Extracting from Files

**Prompt in Claude Desktop:**
```
Extract the content from /path/to/document.pdf
```

**What happens:**
Claude will extract text content from the PDF, including any embedded text, tables, and structural information.

### Working with Videos

**Prompt in Claude Desktop:**
```
Please extract the transcript from /path/to/video.mp4
```

**What happens:**
Content Core will extract audio from the video, transcribe it to text, and return the full transcript.

### Complex Workflows

**Prompt in Claude Desktop:**
```
Extract content from https://www.youtube.com/watch?v=example and summarize the key points in bullet format
```

**What happens:**
1. Claude extracts the YouTube video transcript using the MCP server
2. Claude then processes and summarizes the content as requested

## Response Format

The MCP server returns structured JSON responses:

```json
{
  "success": true,
  "error": null,
  "source_type": "url",
  "source": "https://example.com/article",
  "content": "Extracted article content...",
  "metadata": {
    "extraction_time_seconds": 2.34,
    "extraction_timestamp": "2025-06-19T13:00:00Z",
    "content_length": 1234,
    "identified_type": "text/html",
    "title": "Article Title",
    "final_url": "https://example.com/article",
    // Additional metadata specific to content type
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "File not found: /path/to/nonexistent.pdf",
  "source_type": "file",
  "source": "/path/to/nonexistent.pdf",
  "content": null,
  "metadata": {
    "extraction_timestamp": "2025-06-19T13:00:00Z",
    "error_type": "FileNotFoundError"
  }
}
```

## Supported Content Types

The MCP server supports all content types that Content Core can handle:

### Web Content
- HTML pages
- YouTube videos (transcript extraction)
- Social media posts
- Articles and blogs
- Documentation sites

### Document Formats
- PDF files
- Microsoft Word (.docx)
- PowerPoint (.pptx)
- Excel (.xlsx)
- Markdown files
- Plain text files
- CSV files

### Media Files
- Video files (MP4, AVI, MOV, etc.) - extracts transcript
- Audio files (MP3, WAV, M4A, etc.) - transcribes to text
- Images (JPG, PNG, etc.) - OCR text extraction

### Other Formats
- ZIP archives (extracts text from contained files)
- EPUB books
- AsciiDoc files
- HTML files

## Configuration

### Engine Selection

Content Core's MCP server uses the 'auto' engine by default, which automatically selects the best extraction method based on:

- **URLs**: Firecrawl (if API key available) → Jina (if API key available) → BeautifulSoup
- **Files**: Docling → Simple extraction

### API Keys

To get the best extraction results, configure these API keys:

**Required for Audio/Video Processing:**
```bash
# Essential for transcribing audio and video files
export OPENAI_API_KEY="sk-your-openai-key-here"
```

**Optional but Recommended for Web Extraction:**
```bash
# For enhanced web crawling (recommended)
export FIRECRAWL_API_KEY="fc-your-firecrawl-key-here"

# Alternative web crawling service (fallback)
export JINA_API_KEY="jina-your-jina-key-here"
```

**Additional AI Models (Optional):**
```bash
# For alternative AI models
export GOOGLE_API_KEY="your-google-key"
```

**What happens without these keys:**
- **No OPENAI_API_KEY**: Audio/video transcription will fail
- **No web crawling keys**: URLs will use basic BeautifulSoup extraction (less reliable)
- **No AI model keys**: Content cleaning/summarization features won't work

**Getting API Keys:**
- **OpenAI**: Visit [OpenAI API Keys](https://platform.openai.com/api-keys)
- **Firecrawl**: Visit [Firecrawl](https://www.firecrawl.dev/) for enhanced web scraping
- **Jina**: Visit [Jina AI](https://jina.ai/) for alternative web extraction

### Engine Selection via Environment Variables

For advanced users, you can override the extraction engines:

```json
{
  "mcpServers": {
    "content-core": {
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "FIRECRAWL_API_KEY": "fc-...",
        "CCORE_DOCUMENT_ENGINE": "simple",    // Skip docling, use PyMuPDF
        "CCORE_URL_ENGINE": "auto"       // Or firecrawl, jina
      }
    }
  }
}
```

**Available engines:**
- **Document**: `auto`, `simple`, `docling` (requires `content-core[docling]`)
- **URL**: `auto`, `simple`, `firecrawl`, `jina`

**Use cases:**
- Set `CCORE_DOCUMENT_ENGINE=simple` to avoid docling dependency issues
- Set `CCORE_URL_ENGINE=firecrawl` to always use paid service for better reliability
- Set `CCORE_URL_ENGINE=simple` for faster processing without external API calls

### Custom Prompts

You can customize Content Core's behavior by setting a custom prompt path:

```bash
export PROMPT_PATH="/path/to/your/custom/prompts"
```

## Troubleshooting

### Common Issues

**"MCP content-core: Unexpected token" errors:**
- This usually indicates output to stdout that interferes with the MCP protocol
- Content Core v1.0.5+ includes fixes to suppress MoviePy and other library outputs

**Connection failures:**
```bash
# Test the MCP server directly
content-core-mcp

# Or with uvx
uvx --from "content-core" content-core-mcp
```

**Missing dependencies:**
```bash
# Reinstall Content Core
pip install --force-reinstall content-core
```

**Audio/video extraction failing:**
- Make sure `OPENAI_API_KEY` is set in your environment variables
- Check that your OpenAI API key has sufficient credits
- Audio/video files require OpenAI's Whisper API for transcription

**Poor web extraction quality:**
- Add `FIRECRAWL_API_KEY` for better web scraping results
- Add `JINA_API_KEY` as a fallback option
- Without these keys, basic BeautifulSoup extraction is used (limited functionality)

### Debug Mode

For development and debugging, you can run the server with additional logging:

```bash
# Set debug level
export LOGURU_LEVEL=DEBUG
content-core-mcp
```

### Performance Considerations

- **Large files**: Video and audio files may take longer to process due to transcription
- **API rate limits**: Some web extraction services have rate limits
- **Network connectivity**: URL extraction requires internet access

## Development

### Running Locally

```bash
# Clone the repository
git clone https://github.com/lfnovo/content-core
cd content-core

# Install with MCP dependencies
uv sync --extra mcp

# Run the server
make mcp-server
# or
uv run content-core-mcp
```

### Testing

```bash
# Run MCP-specific tests
uv run pytest tests/unit/test_mcp_server.py -v

# Run all tests
make test
```

## Contributing

Contributions to the MCP server are welcome! Please see our [Contributing Guide](../CONTRIBUTING.md) for development setup and guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/lfnovo/content-core/issues)
- **Documentation**: [Main Documentation](usage.md)
- **MCP Protocol**: [Model Context Protocol](https://modelcontextprotocol.io/)

## Version History

- **v1.0.4**: Initial MCP server implementation
- **v1.0.5**: Added output suppression for better MCP compatibility
- **Latest**: Enhanced error handling and metadata support