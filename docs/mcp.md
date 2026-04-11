# MCP Server

Content Core includes a Model Context Protocol (MCP) server that exposes content extraction and summarization to Claude Desktop and other MCP-compatible applications.

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is an open standard that lets AI applications connect to external tools and data sources. Content Core's MCP server gives Claude the ability to extract content from URLs and files, and to summarize text, directly within a conversation.

## Installation

### With pip

```bash
pip install content-core
```

### With uvx (zero install)

```bash
uvx content-core mcp
```

## Claude Desktop Setup

Add the following to your `claude_desktop_config.json`:

**Config file location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### Recommended Configuration

```json
{
  "mcpServers": {
    "content-core": {
      "command": "uvx",
      "args": ["content-core", "mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here"
      }
    }
  }
}
```

### With Additional API Keys

For best results with URL extraction, add web crawling API keys:

```json
{
  "mcpServers": {
    "content-core": {
      "command": "uvx",
      "args": ["content-core", "mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "FIRECRAWL_API_KEY": "fc-your-key-here",
        "JINA_API_KEY": "jina-your-key-here"
      }
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
        "content-core",
        "mcp"
      ]
    }
  }
}
```

## Available Tools

The MCP server provides two tools. Both return plain text responses.

### extract_content

Extracts content from a URL or file.

**Parameters:**
- `url` (string, optional) -- URL to extract content from
- `file_path` (string, optional) -- local file path to extract content from
- `engine` (string, optional) -- extraction engine override

Exactly one of `url` or `file_path` must be provided.

### summarize_content

Summarizes text content using an LLM.

**Parameters:**
- `content` (string, required) -- the text to summarize
- `context` (string, optional) -- guidance for the summary style (e.g., "bullet points", "explain to a child", "action items")

## Usage Examples

Once configured, you can use these tools naturally in Claude Desktop conversations:

**Extracting a web page:**
> "Extract the content from https://example.com/article"

**Extracting a local file:**
> "Read the content of /path/to/document.pdf"

**Transcribing a video:**
> "Extract the transcript from /path/to/lecture.mp4"

**Summarizing extracted content:**
> "Extract https://example.com/long-article and summarize it in bullet points"

Claude will call the appropriate MCP tools automatically based on your request.

## Configuration via Environment Variables

Engine selection and other settings can be passed through the `env` block in the Claude Desktop config:

```json
{
  "mcpServers": {
    "content-core": {
      "command": "uvx",
      "args": ["content-core", "mcp"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "CCORE_URL_ENGINE": "firecrawl",
        "CCORE_DOCUMENT_ENGINE": "simple",
        "CCORE_AUDIO_CONCURRENCY": "5",
        "CCORE_FIRECRAWL_API_URL": "http://localhost:3002"
      }
    }
  }
}
```

See the [usage guide](usage.md) for the full list of `CCORE_` environment variables.

## API Keys

| Key | Purpose | Required? |
|-----|---------|-----------|
| `OPENAI_API_KEY` | Audio/video transcription, summarization | Required for media and summarization |
| `FIRECRAWL_API_KEY` | High-quality web extraction | Optional (improves URL extraction) |
| `JINA_API_KEY` | Alternative web extraction | Optional (avoids Jina rate limits) |

Without `OPENAI_API_KEY`, audio/video transcription and summarization will not work. Without web crawling API keys, URL extraction falls back to BeautifulSoup.

**Getting API keys:**
- OpenAI: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Firecrawl: [firecrawl.dev](https://www.firecrawl.dev/) or [self-host](https://github.com/mendableai/firecrawl/blob/main/SELF_HOST.md)
- Jina: [jina.ai](https://jina.ai/)

## Troubleshooting

**"Unexpected token" errors in Claude Desktop:**
- Usually caused by library output leaking to stdout. Update to the latest version of content-core.

**Connection failures:**
```bash
# Test the MCP server directly
content-core mcp

# Or with uvx
uvx content-core mcp
```

**Audio/video extraction failing:**
- Verify `OPENAI_API_KEY` is set and has sufficient credits.

**Poor web extraction quality:**
- Add `FIRECRAWL_API_KEY` or `JINA_API_KEY` for better results.

**Debug logging:**
```bash
export LOGURU_LEVEL=DEBUG
content-core mcp
```
