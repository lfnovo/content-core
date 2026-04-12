# CLI Reference

Content Core provides a unified command-line interface for extracting and summarizing content.

## Installation

```bash
pip install content-core
```

Or use without installation via uvx:

```bash
uvx content-core <command> [options]
```

## Commands

### extract

Extract content from a URL, file, or text.

```
content-core extract [OPTIONS] SOURCE
```

**Arguments:**
- `SOURCE` — URL, file path, or text to extract from

**Options:**
- `-f, --format [text|json]` — Output format (default: text)
- `--engine [firecrawl|jina|crawl4ai|simple]` — Override URL extraction engine
- `--debug` — Enable debug logging

**Examples:**

```bash
# Extract from URL
content-core extract "https://example.com"

# Extract from file
content-core extract document.pdf

# Extract with JSON output
content-core extract --format json "https://example.com"

# Extract with specific engine
content-core extract --engine firecrawl "https://example.com"

# With uvx (no installation)
uvx content-core extract "https://example.com"
```

### summarize

Summarize content using LLM. Requires an LLM API key (e.g., OPENAI_API_KEY).

```
content-core summarize [OPTIONS] [CONTENT]
```

**Arguments:**
- `CONTENT` — Text to summarize (optional, reads from stdin if not provided)

**Options:**
- `--context TEXT` — Context for summarization (e.g., "bullet points", "explain to a child")
- `--debug` — Enable debug logging

**Examples:**

```bash
# Summarize text
content-core summarize "Long text to summarize..."

# Summarize with context
content-core summarize --context "bullet points" "Long text..."

# Pipe from extraction
content-core extract "https://example.com" | content-core summarize

# Pipe from file
cat article.txt | content-core summarize --context "one paragraph"
```

### mcp

Start the MCP (Model Context Protocol) server for Claude Desktop integration.

```
content-core mcp
```

See [MCP documentation](mcp.md) for setup instructions.

## Global Options

- `--debug` — Enable debug logging (place before the subcommand)

```bash
content-core --debug extract "https://example.com"
```

## Configuration

The CLI reads configuration from environment variables with the `CCORE_` prefix:

```bash
export CCORE_URL_ENGINE=firecrawl
export CCORE_DOCUMENT_ENGINE=auto
export OPENAI_API_KEY=sk-...

content-core extract "https://example.com"
```

The `--engine` flag overrides `CCORE_URL_ENGINE` for a single invocation.

See [Usage documentation](usage.md) for all configuration options.
