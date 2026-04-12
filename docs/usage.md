# Using the Content Core Library

This guide covers the Python API, configuration, and usage patterns for Content Core v2.0.

## Basic Usage

### Extraction

The primary function is `extract_content`, which accepts keyword arguments and returns an `ExtractionOutput`:

```python
import content_core

# Extract from a URL
result = await content_core.extract_content(url="https://example.com")
print(result.content)

# Extract from a file
result = await content_core.extract_content(file_path="document.pdf")
print(result.content)

# Extract from raw text
result = await content_core.extract_content(content="Some text content.")
print(result.content)
```

### Summarization

```python
import content_core

summary = await content_core.summarize("Long article text here...", context="bullet points")
print(summary)

# Other context examples
summary = await content_core.summarize(text, context="explain to a child")
summary = await content_core.summarize(text, context="executive summary")
summary = await content_core.summarize(text, context="action items")
```

## Extraction by Source Type

### URLs

```python
# Auto-detect best engine
result = await content_core.extract_content(url="https://example.com")

# Force a specific engine
from content_core import ContentCoreConfig
config = ContentCoreConfig(url_engine="firecrawl")
result = await content_core.extract_content(url="https://example.com", config=config)
```

### Documents

```python
# PDF
result = await content_core.extract_content(file_path="report.pdf")

# Word document
result = await content_core.extract_content(file_path="document.docx")

# PowerPoint
result = await content_core.extract_content(file_path="slides.pptx")

# Excel
result = await content_core.extract_content(file_path="data.xlsx")

# Use Docling engine for richer parsing
from content_core import ContentCoreConfig
config = ContentCoreConfig(document_engine="docling", docling_output_format="html")
result = await content_core.extract_content(file_path="report.pdf", config=config)
```

### Audio and Video

```python
# Audio transcription
result = await content_core.extract_content(file_path="interview.mp3")

# Video (audio is extracted and transcribed automatically)
result = await content_core.extract_content(file_path="lecture.mp4")

# With custom speech-to-text model
from content_core import ContentCoreConfig
config = ContentCoreConfig(audio_provider="openai", audio_model="whisper-1")
result = await content_core.extract_content(file_path="interview.mp3", config=config)
```

### YouTube

```python
result = await content_core.extract_content(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(result.content)  # Video transcript
```

### Text with HTML Auto-Detection

```python
# Plain text passes through unchanged
result = await content_core.extract_content(content="Plain text here.")

# HTML content is automatically detected and converted to markdown
result = await content_core.extract_content(
    content="<h1>Title</h1><p>Paragraph with <a href='url'>link</a></p>"
)
```

## Configuration

Content Core uses `ContentCoreConfig` backed by pydantic-settings. Configuration is resolved in priority order:

1. **Constructor args** (Python API) or **command flags** (CLI) — highest priority
2. **Environment variables** (`CCORE_*` prefix)
3. **Config file** (`~/.content-core/config.toml`)
4. **Defaults** — lowest priority

### Config File

Set persistent defaults via CLI or edit the file directly:

```bash
content-core config set llm_provider anthropic
content-core config set llm_model claude-sonnet-4-20250514
content-core config set url_engine firecrawl
```

Or edit `~/.content-core/config.toml`:

```toml
llm_provider = "anthropic"
llm_model = "claude-sonnet-4-20250514"
url_engine = "firecrawl"
youtube_languages = ["en", "pt"]
```

### In Code

```python
from content_core import ContentCoreConfig

config = ContentCoreConfig(
    url_engine="firecrawl",
    document_engine="docling",
    audio_concurrency=5,
    llm_provider="openai",
    llm_model="gpt-4o-mini",
    stt_provider="openai",
    stt_model="whisper-1",
    stt_timeout=3600,
    youtube_languages=["en", "pt"],
)

result = await content_core.extract_content(url="https://example.com", config=config)
```

### Via Environment Variables

All config fields use the `CCORE_` prefix:

```bash
CCORE_URL_ENGINE=firecrawl
CCORE_DOCUMENT_ENGINE=auto
CCORE_AUDIO_CONCURRENCY=5
CCORE_LLM_PROVIDER=openai
CCORE_LLM_MODEL=gpt-4o-mini
CCORE_STT_PROVIDER=openai
CCORE_STT_MODEL=whisper-1
CCORE_STT_TIMEOUT=3600
CCORE_YOUTUBE_LANGUAGES=en,pt
CCORE_FIRECRAWL_PROXY=auto
CCORE_FIRECRAWL_WAIT_FOR=3000
FIRECRAWL_API_URL=http://localhost:3002
CRAWL4AI_API_URL=http://localhost:11235
```

API keys for external services use their standard variable names:

```bash
OPENAI_API_KEY=sk-...
FIRECRAWL_API_KEY=fc-...
JINA_API_KEY=jina-...
```

## Engine Selection

### URL Engines

The `url_engine` setting controls how web pages are extracted:

| Engine | Description | Requirements |
|--------|-------------|-------------|
| `auto` (default) | Tries engines in order: Firecrawl, Jina, Crawl4AI, BeautifulSoup | Depends on available API keys |
| `simple` | BeautifulSoup-based extraction | None |
| `firecrawl` | Firecrawl API | `FIRECRAWL_API_KEY` |
| `jina` | Jina Reader API | Optional `JINA_API_KEY` |
| `crawl4ai` | Local browser-based extraction | `pip install content-core[crawl4ai]` + Playwright |

For self-hosted Firecrawl, set `FIRECRAWL_API_URL` to your instance URL.

### Document Engines

The `document_engine` setting controls how files (PDF, DOCX, PPTX, XLSX) are processed:

| Engine | Description | Requirements |
|--------|-------------|-------------|
| `auto` (default) | Tries Docling first, falls back to simple | Depends on installed extras |
| `simple` | pdfplumber for PDF, fast-ebook for EPUB, python-docx/openpyxl/python-pptx for Office | None (included) |
| `docling` | Docling library for rich document parsing | `pip install content-core[docling]` |

## AI Providers

Content Core uses [Esperanto](https://github.com/lfnovo/esperanto) as a unified abstraction layer for LLM and Speech-to-Text providers. This means you can use any provider supported by Esperanto without changing your code — just update the config.

### Supported Providers

| Provider | LLM | STT | API Key |
|----------|-----|-----|---------|
| `openai` (default) | GPT-4o, GPT-4o-mini, etc. | Whisper | `OPENAI_API_KEY` |
| `anthropic` | Claude Sonnet, Claude Opus, etc. | — | `ANTHROPIC_API_KEY` |
| `google` | Gemini models | — | `GOOGLE_API_KEY` |
| `groq` | LLaMA, Mixtral, etc. | Whisper | `GROQ_API_KEY` |
| `deepseek` | DeepSeek models | — | `DEEPSEEK_API_KEY` |
| `ollama` | Local models | — | — (local) |
| `openrouter` | Multiple providers | — | `OPENROUTER_API_KEY` |

For a complete and up-to-date list of providers and models, see the [Esperanto documentation](https://github.com/lfnovo/esperanto).

### LLM Configuration (Summarization)

```bash
# Via config file (persistent)
content-core config set llm_provider anthropic
content-core config set llm_model claude-sonnet-4-20250514

# Via environment variables (per-session)
export CCORE_LLM_PROVIDER=anthropic
export CCORE_LLM_MODEL=claude-sonnet-4-20250514
```

```python
# Via Python API (per-call)
config = ContentCoreConfig(llm_provider="anthropic", llm_model="claude-sonnet-4-20250514")
summary = await content_core.summarize("text", "bullet points", config=config)
```

Use `summary_model` to set a different model specifically for summarization while keeping `llm_model` as the default for other LLM operations.

### STT Configuration (Audio/Video Transcription)

```bash
# Via config file (persistent)
content-core config set stt_provider openai
content-core config set stt_model whisper-1

# Via environment variables (per-session)
export CCORE_STT_PROVIDER=openai
export CCORE_STT_MODEL=whisper-1
```

```python
# Via Python API (per-call)
config = ContentCoreConfig(stt_provider="openai", stt_model="whisper-1")
result = await content_core.extract_content(file_path="audio.mp3", config=config)
```

Use `audio_provider` and `audio_model` together to override the STT provider for a specific call without changing the default.

## Audio Processing

Long audio files are automatically split into segments and transcribed in parallel.

### Concurrency

Control the number of simultaneous transcriptions (1-10, default 3):

```bash
CCORE_AUDIO_CONCURRENCY=5
```

Or in code:

```python
config = ContentCoreConfig(audio_concurrency=5)
```

Higher values speed up processing of long files but may hit API rate limits.

### Custom STT Models

Override the speech-to-text provider and model per call:

```python
config = ContentCoreConfig(audio_provider="openai", audio_model="whisper-1")
result = await content_core.extract_content(file_path="audio.mp3", config=config)
```

Both `audio_provider` and `audio_model` must be specified together. If only one is provided, the default model is used and a warning is logged.

## Docling Integration

Docling provides advanced document parsing for PDF, DOCX, PPTX, XLSX, Markdown, AsciiDoc, HTML, CSV, and images.

### Installation

```bash
pip install content-core[docling]
```

### Usage

```python
# Set globally via config
config = ContentCoreConfig(document_engine="docling")

# Or per-call
config = ContentCoreConfig(document_engine="docling", docling_output_format="html")
result = await content_core.extract_content(file_path="report.pdf", config=config)
```

### Enrichment Features

Docling supports optional enrichment features that require additional models. These are disabled by default to avoid extra download and processing time.

| Flag | What it does | Default | Impact |
|------|-------------|---------|--------|
| `docling_ocr` | OCR for scanned PDFs | `true` | Medium — runs per page |
| `docling_formulas` | Extract equations as LaTeX | `false` | High — downloads ~500MB model, CPU/CUDA only |
| `docling_vision` | Image descriptions + chart data extraction | `false` | High — downloads ~2GB model |

#### Via config file (persistent)

```bash
content-core config set docling_formulas true
content-core config set docling_vision true
```

#### Via CLI (per-call)

```bash
content-core extract --engine docling --formulas paper.pdf
content-core extract --engine docling --pictures --no-ocr paper.pdf
```

#### Via Python API

```python
from content_core import ContentCoreConfig

config = ContentCoreConfig(
    document_engine="docling",
    docling_formulas=True,
    docling_vision=True,
)
result = await content_core.extract_content(file_path="paper.pdf", config=config)
```

#### Via MCP

The `extract_content` MCP tool accepts `formulas`, `pictures`, and `no_ocr` parameters:

```
extract_content(file_path="paper.pdf", engine="docling", formulas=true, pictures=true)
```

> **Note:** Enrichment flags are only applied when `document_engine="docling"`. A warning is logged if flags are set without the Docling engine.

## Proxy Configuration

Content Core uses standard HTTP proxy environment variables:

```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1,internal.example.com

# With authentication
HTTP_PROXY=http://user:password@proxy.example.com:8080
```

All network requests (aiohttp, YouTube fetching, Crawl4AI, Esperanto models) automatically use these variables. No additional Content Core configuration is needed.

Note: Firecrawl does not support client-side proxy configuration. Configure proxy on the Firecrawl server side instead.

## Custom Prompt Templates

Content Core uses built-in prompts for summarization. You can override them by setting the `PROMPT_PATH` environment variable:

```bash
PROMPT_PATH=/path/to/your/custom/prompts
```

When a prompt template is requested, Content Core checks your custom directory first. If the template is not found there, it falls back to the built-in prompts.

## Retry Behavior

Content Core automatically retries transient failures (network timeouts, API rate limits, connection errors) with exponential backoff and jitter. This applies to all external operations including URL extraction, audio transcription, YouTube fetching, and LLM calls.

Retries are configured with sensible defaults and require no setup. If you need to tune retry behavior for specific scenarios (e.g., aggressive rate limits), you can override settings via environment variables:

```bash
# Pattern: CCORE_{OPERATION}_{PARAM}
CCORE_YOUTUBE_MAX_RETRIES=10
CCORE_URL_API_MAX_RETRIES=5
CCORE_AUDIO_MAX_RETRIES=5
```

## File Type Detection

Content Core uses a pure Python file type detector based on binary signatures and content analysis. No system dependencies (like libmagic) are required. Detection works regardless of file extension and supports 25+ formats across documents, images, media, text, and archives.
