# Content Core

Library for extracting and summarizing content from URLs, files, and text.

## Commands

- **Install dependencies**: `uv sync --group dev`
- **Run tests**: `make test` (unit + integration) or `uv run pytest -v`
- **Run single test**: `uv run pytest -k "test_name"`
- **Run e2e tests**: `make test-e2e` (requires network + API keys)
- **Run all tests**: `make test-all`
- **Linting**: `make ruff` (runs `ruff check . --fix`)
- **Build package**: `uv build`

## CLI

```bash
content-core extract <source> [--format text|json] [--engine ENGINE]
content-core summarize [content] [--context CONTEXT]
content-core mcp
content-core config list|set|delete
```

## Codebase Structure

```
src/content_core/
├── __init__.py              # Public API: extract_content, summarize, ContentCoreConfig
├── config.py                # ContentCoreConfig (pydantic-settings, env prefix CCORE_)
├── extraction.py            # Main orchestrator — routes input to processors
├── models.py                # ModelFactory for Esperanto LLM/STT models
├── cli.py                   # Click CLI: extract, summarize, mcp subcommands
├── logging.py               # Loguru configuration
├── templated_message.py     # LLM prompt execution with Jinja templates
│
├── common/
│   ├── exceptions.py        # Exception hierarchy (ContentCoreError base)
│   ├── retry.py             # Self-contained retry decorators with tenacity
│   ├── state.py             # ExtractionInput, ExtractionOutput data models
│   └── types.py             # Type aliases (DocumentEngine, UrlEngine)
│
├── content/
│   ├── summary/core.py      # Content summarization via LLM
│   └── identification/      # File type detection (pure Python)
│
├── processors/
│   ├── protocol.py          # Processor Protocol definition
│   ├── text.py              # Plain text + HTML-to-markdown
│   ├── url/                 # URL extraction engines
│   │   ├── __init__.py      # Engine router + fallback chain
│   │   ├── bs4.py           # BeautifulSoup + readability
│   │   ├── jina.py          # Jina Reader API
│   │   ├── firecrawl.py     # Firecrawl SDK
│   │   ├── reddit.py        # Reddit posts via public JSON endpoint
│   │   ├── youtube.py       # YouTube transcript extraction
│   │   └── crawl4ai.py      # Crawl4AI browser automation
│   ├── document/            # Document extraction
│   │   ├── __init__.py      # Document type router
│   │   ├── pdf.py           # PDF via pdfplumber
│   │   ├── epub.py          # EPUB via fast-ebook
│   │   ├── docx.py          # python-docx
│   │   ├── pptx.py          # python-pptx
│   │   ├── xlsx.py          # openpyxl
│   │   └── docling.py       # Optional Docling integration
│   └── media/               # Audio/video processing
│       ├── __init__.py      # Video→audio pipeline
│       ├── audio.py         # Transcription via Esperanto STT
│       └── video.py         # Video-to-audio extraction
│
├── mcp/
│   └── server.py            # MCP server: extract_content, summarize_content
│
└── tools/                   # Optional LangChain tool wrappers (requires langchain-core)
    ├── extract.py
    └── summarize.py
```

## Architecture

**Data flow**: Input -> `extraction.py` orchestrator -> Processor -> `ExtractionOutput`

1. `ExtractionInput` received (content, URL, or file path)
2. `extraction.py` identifies source type and routes to the appropriate processor
3. Processor extracts content and returns `ExtractionOutput`

**Key patterns**:
- Plain async Python orchestration (no LangGraph)
- Configuration via `ContentCoreConfig` (pydantic-settings, env vars with CCORE_ prefix)
- Processors are async functions taking simple params + config, returning ExtractionOutput
- Retry decorators handle transient failures for network/API operations

## Configuration

Via constructor or environment variables (CCORE_ prefix):

```python
from content_core import ContentCoreConfig
config = ContentCoreConfig(url_engine="firecrawl", audio_concurrency=5)
```

Key settings: `url_engine`, `document_engine`, `audio_provider`, `audio_model`, `firecrawl_api_url`, `youtube_languages`, `llm_provider`, `llm_model`, `docling_ocr`, `docling_formulas`, `docling_vision`

Docling enrichment flags (`docling_ocr`, `docling_formulas`, `docling_vision`) control OCR, formula extraction, and image/chart processing when `document_engine="docling"`. These are also exposed as CLI flags (`--formulas`, `--pictures`, `--no-ocr`) and MCP parameters.

Priority: constructor args > env vars (`CCORE_*`) > config file (`~/.content-core/config.toml`) > defaults

## Code Style

- **Formatting**: PEP 8, enforced by ruff
- **Error handling**: Use custom exceptions from `common/exceptions.py`
- **Tests**: Three tiers — see below

## Testing

### When to use each command

| Command | When to use | Speed |
|---------|------------|-------|
| `make test` | After any code change — default validation | ~12s |
| `uv run pytest -k "keyword"` | After changing a specific area (see table below) | <2s |
| `make test-e2e` | Before a release — validates real APIs and network | ~30s |
| `make test-e2e-heavy` | Docling e2e tests — downloads large models | minutes |
| `make test-e2e-all` | All e2e tests (basic + heavy) | minutes |
| `make test-all` | Full validation, all tiers | varies |

### Targeted test keywords by area

When you change a specific processor or module, run only the relevant tests for fast feedback:

| Area changed | Test command |
|---|---|
| `extraction.py` (orchestrator/routing) | `uv run pytest -k "routing"` |
| `config.py` | `uv run pytest -k "config"` |
| `processors/url/` (any URL engine) | `uv run pytest -k "url_engine"` |
| `processors/url/youtube.py` | `uv run pytest -k "youtube"` |
| `processors/url/reddit.py` | `uv run pytest -k "reddit"` |
| `processors/document/pdf.py` | `uv run pytest -k "pdf"` |
| `processors/document/docx.py` or `pptx.py` or `xlsx.py` | `uv run pytest -k "office"` |
| `processors/document/docling.py` | `uv run pytest -k "docling"` |
| `processors/text.py` | `uv run pytest -k "text_processing"` |
| `processors/media/audio.py` | `uv run pytest -k "audio or media_pipeline"` |
| `processors/media/video.py` | `uv run pytest -k "media_pipeline"` |
| `mcp/server.py` | `uv run pytest -k "mcp"` |
| `cli.py` | `uv run pytest -k "cli"` |
| `common/retry.py` | `uv run pytest -k "retry"` |
| `content/identification/` | `uv run pytest -k "file_detector"` |
| `common/state.py` (models) | `uv run pytest -k "models"` |

### Test structure

```
tests/
├── unit/              # Fast, mocked, no I/O or network (~263 tests)
│   ├── test_routing.py            # Orchestrator: input → correct processor
│   ├── test_config_v2.py          # ContentCoreConfig defaults, env vars, validation
│   ├── test_url_engine_select.py  # URL engine: auto/firecrawl/jina/simple
│   ├── test_youtube_parsing.py    # YouTube ID extraction, transcript fallbacks
│   ├── test_reddit_extraction.py  # Reddit URL detection, JSON parsing, formatting
│   ├── test_pdf_extraction.py     # PDF text cleaning, extraction with mocked pdfplumber
│   ├── test_pdf_helpers.py        # Formula detection, table conversion helpers
│   ├── test_epub_extraction.py    # EPUB extraction with mocked fast-ebook
│   ├── test_office_extraction.py  # DOCX/PPTX/XLSX routing and extraction
│   ├── test_docling_extraction.py # Docling output formats with mocked converter
│   ├── test_text_processing.py    # HTML detection, markdown conversion
│   ├── test_media_pipeline.py     # Audio transcription, video pipeline, stream selection
│   ├── test_audio_concurrency.py  # Semaphore, ordering, concurrency limits
│   ├── test_mcp_v2.py             # MCP tools: extract + summarize
│   ├── test_cli.py                # CLI: _build_input, commands, config subcommands
│   ├── test_config_file.py        # TOML config file: read/write, set/delete, precedence
│   ├── test_models_v2.py          # ExtractionInput/Output, Processor Protocol
│   ├── test_retry.py              # Retry decorators, exception classification
│   └── test_file_detector*.py     # MIME detection, performance, edge cases
│
├── integration/       # Local files, no network (~22 tests)
│   ├── test_extraction.py   # Real file extraction (PDF, DOCX, PPTX, XLSX, EPUB, etc.)
│   └── test_cli_v2.py       # CLI subcommands via CliRunner with real extraction
│
└── e2e/
    ├── [e2e] test_url_engines.py   # Firecrawl, Jina, Crawl4AI, BS4 with real URLs
    ├── [e2e] test_youtube.py       # Real YouTube transcript extraction
    ├── [e2e] test_remote.py        # Remote PDF download from arxiv
    ├── [e2e] test_media.py         # Audio/video transcription via STT API
    └── [e2e_heavy] test_docling.py # Docling extraction with enrichment flags
```
