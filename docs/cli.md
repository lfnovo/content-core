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
- `--engine ENGINE` — Override extraction engine (routed automatically based on input type)
- `--formulas` — Enable formula extraction as LaTeX (Docling only)
- `--pictures` — Enable image description + chart data extraction (Docling only)
- `--no-ocr` — Disable OCR (Docling only)

**Examples:**

```bash
# Extract from URL
content-core extract "https://example.com"

# Extract from file
content-core extract document.pdf

# Extract with JSON output
content-core extract --format json "https://example.com"

# Extract URL with specific engine
content-core extract --engine firecrawl "https://example.com"

# Extract document with specific engine
content-core extract --engine docling document.pdf

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

### config

Manage persistent configuration stored in `~/.content-core/config.toml`.

```
content-core config <subcommand>
```

**Subcommands:**

#### config list

List all values in the config file.

```bash
content-core config list
```

#### config set

Set a config value.

```
content-core config set KEY VALUE
```

```bash
# Set LLM provider
content-core config set llm_provider anthropic

# Set LLM model
content-core config set llm_model claude-sonnet-4-20250514

# Set YouTube languages (comma-separated)
content-core config set youtube_languages en,pt,es

# Set audio concurrency
content-core config set audio_concurrency 5
```

#### config delete

Delete a config value.

```
content-core config delete KEY
```

```bash
content-core config delete llm_provider
```

**Available keys:**

| Key | Description | Default |
|-----|-------------|---------|
| `audio_concurrency` | Parallel transcription limit (1-10) | `3` |
| `audio_model` | Override STT model | — |
| `crawl4ai_api_url` | Crawl4AI Docker API URL (omit for local mode) | — |
| `audio_provider` | Override STT provider | — |
| `docling_formulas` | Enable formula extraction | `false` |
| `docling_ocr` | Enable OCR for scanned PDFs | `true` |
| `docling_output_format` | Docling output format | `markdown` |
| `docling_vision` | Enable image description + chart data extraction | `false` |
| `document_engine` | Document extraction engine (`auto`, `simple`, `docling`) | `auto` |
| `firecrawl_api_url` | Firecrawl API URL | `https://api.firecrawl.dev` |
| `firecrawl_proxy` | Firecrawl proxy mode (`auto`, `basic`, `stealth`) | `auto` |
| `firecrawl_wait_for` | Wait time in ms before extraction | `3000` |
| `llm_model` | LLM model for summarization | `gpt-4o-mini` |
| `llm_provider` | LLM provider | `openai` |
| `stt_model` | Speech-to-text model | `whisper-1` |
| `stt_provider` | Speech-to-text provider | `openai` |
| `stt_timeout` | STT API timeout in seconds | `3600` |
| `summary_model` | Override LLM model for summarization | — |
| `url_engine` | URL extraction engine (`auto`, `simple`, `firecrawl`, `jina`, `crawl4ai`) | `auto` |
| `youtube_languages` | Transcript languages, comma-separated | `en,es,pt` |

Run `content-core config --help` to see this list in the terminal.

## Global Options

- `--debug` — Enable debug logging (place before the subcommand)

```bash
content-core --debug extract "https://example.com"
```

## Configuration

Configuration is resolved in the following priority order:

1. **Command flags** (`--engine`) — highest priority
2. **Environment variables** (`CCORE_*` prefix)
3. **Config file** (`~/.content-core/config.toml`)
4. **Defaults** — lowest priority

### Config file

Set persistent defaults with `content-core config set`:

```bash
content-core config set llm_provider anthropic
content-core config set llm_model claude-sonnet-4-20250514
content-core config set url_engine firecrawl
```

Or edit `~/.content-core/config.toml` directly:

```toml
llm_provider = "anthropic"
llm_model = "claude-sonnet-4-20250514"
url_engine = "firecrawl"
```

### Environment variables

Override config file values per-session with `CCORE_` prefix:

```bash
export CCORE_URL_ENGINE=firecrawl
export OPENAI_API_KEY=sk-...
```

### Engine flag

The `--engine` flag is routed automatically based on input type:
- **URLs** → overrides `url_engine` (options: `firecrawl`, `jina`, `crawl4ai`, `simple`)
- **Files** → overrides `document_engine` (options: `docling`, `simple`)

See [Usage documentation](usage.md) for all configuration options.
