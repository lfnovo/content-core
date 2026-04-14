---
name: content-core
description: >
  Extract text content from external sources — URLs, PDFs, documents, YouTube videos, and audio/video files.
  Use when you need to read, analyze, or summarize content from a URL, file, or media source.
allowed-tools:
  - Read
  - Bash
  - Grep
  - Glob
---

## Purpose

Content Core extracts text from external sources so you can read, analyze, or summarize them. Use it whenever you need content from a URL, PDF, document, YouTube video, or audio/video file.

Most extraction works without API keys. Only audio/video transcription and summarization require an LLM API key (e.g., `OPENAI_API_KEY`).

## Prerequisites

Content Core runs via `uvx` (zero-install) which requires `uv` to be available.

### Check if uv is installed

```bash
uv --version
```

If `uv` is not found, help the user install it:

- **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Homebrew**: `brew install uv`
- **pip**: `pip install uv`

After installation, the user may need to restart their shell or run `source ~/.bashrc` / `source ~/.zshrc` for `uv` to be available on PATH.

## Capabilities

| Source | Examples | API Key Needed |
|--------|----------|----------------|
| Web pages | Any URL | No |
| YouTube | Video transcript | No |
| Documents | PDF, DOCX, PPTX, XLSX, EPUB, Markdown | No |
| Audio | MP3, WAV, M4A, FLAC, OGG | Yes (STT) |
| Video | MP4, AVI, MOV, MKV | Yes (STT) |
| Plain text / HTML | Raw text, auto-detects HTML | No |

## CLI Usage

All commands use `uvx content-core` which runs without installation.

### Extract content

```bash
# From a URL
uvx content-core extract "https://example.com"

# From a file
uvx content-core extract document.pdf

# From a YouTube video
uvx content-core extract "https://www.youtube.com/watch?v=VIDEO_ID"

# JSON output (includes title, content, metadata)
uvx content-core extract --format json "https://example.com"

# With a specific extraction engine
uvx content-core extract --engine firecrawl "https://example.com"
uvx content-core extract --engine docling document.pdf
```

### Docling enrichment flags (for advanced document processing)

```bash
# Enable formula extraction (LaTeX)
uvx content-core extract --engine docling --formulas paper.pdf

# Enable image descriptions and chart data extraction
uvx content-core extract --engine docling --pictures paper.pdf

# Disable OCR (faster, for PDFs with embedded text)
uvx content-core extract --engine docling --no-ocr paper.pdf
```

### Summarize content

Requires an LLM API key (`OPENAI_API_KEY` or another provider).

```bash
# Summarize text
uvx content-core summarize "Long text here..."

# With context to guide the summary
uvx content-core summarize --context "bullet points" "Long text..."

# Pipe extraction into summarization
uvx content-core extract "https://example.com" | uvx content-core summarize --context "key takeaways"
```

### Configuration

```bash
# View current config
uvx content-core config list

# Set persistent defaults
uvx content-core config set llm_provider anthropic
uvx content-core config set llm_model claude-sonnet-4-20250514
uvx content-core config set url_engine firecrawl

# Delete a config value
uvx content-core config delete llm_provider

# See all available config keys
uvx content-core config --help
```

## MCP Usage

Content Core can also run as an MCP server. It may or may not be available in your current environment.

### Check availability

Look for `content-core` in the list of available MCP servers. If available, you will have access to these tools:

### extract_content

Extracts text from a URL or file. No API key needed for most sources.

```
extract_content(url="https://example.com")
extract_content(file_path="/path/to/document.pdf")
extract_content(url="https://youtube.com/watch?v=ID")

# With engine override
extract_content(file_path="paper.pdf", engine="docling")

# With Docling enrichment
extract_content(file_path="paper.pdf", engine="docling", formulas=true, pictures=true)
```

### summarize_content

Summarizes text using an LLM. Requires an API key.

```
summarize_content(content="Long text...", context="bullet points")
```

If summarization fails with an API key error, fall back to `extract_content` and return the raw content instead.

## Guidelines

- For small/medium content (articles, short pages): prefer MCP tools if available — they are async and more efficient
- For large content (long documents, full books, lengthy transcripts): prefer the CLI via Bash, redirecting output to a file (`uvx content-core extract "URL" > output.md`). This avoids flooding the agent's context window with large payloads. Read only the relevant sections from the file as needed.
- If MCP is not available, always use the CLI via Bash with `uvx content-core`
- For URLs: extraction works without any API key
- For audio/video: requires `OPENAI_API_KEY` (or another STT provider key)
- For summarization: requires an LLM API key
- When summarization is unavailable, extract the raw content and summarize it yourself
- Use `--format json` when you need structured metadata (title, source type, identified type)
- For large documents with formulas or charts, use `--engine docling` with `--formulas` or `--pictures`

## Error Handling

- If `uvx` is not found: help the user install `uv` (see Prerequisites above)
- If extraction returns empty content: the source may be behind a paywall or require authentication
- If MCP tools are not available: fall back to CLI via `uvx content-core`
- If summarization fails with API key error: use `extract_content` instead and summarize the content yourself
- If a specific engine fails: try without `--engine` to use the auto-detection fallback chain
