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
```

## Codebase Structure

```
src/content_core/
├── __init__.py              # Public API: extract_content, summarize, ContentCoreConfig
├── config.py                # ContentCoreConfig (pydantic-settings, env prefix CCORE_)
├── extraction.py            # Main orchestrator — routes input to processors
├── models.py                # ModelFactory for Esperanto LLM/STT models
├── models_v2.py             # ExtractionInput, ExtractionOutput data models
├── cli.py                   # Click CLI: extract, summarize, mcp subcommands
├── logging.py               # Loguru configuration
├── templated_message.py     # LLM prompt execution with Jinja templates
│
├── common/
│   ├── exceptions.py        # Exception hierarchy (ContentCoreError base)
│   ├── retry.py             # Self-contained retry decorators with tenacity
│   ├── state.py             # Data models + backward compat aliases
│   └── types.py             # Type aliases (DocumentEngine, UrlEngine)
│
├── content/
│   ├── summary/core.py      # Content summarization via LLM
│   └── identification/      # File type detection (pure Python)
│
├── processors/
│   ├── protocol.py          # Processor Protocol definition
│   ├── youtube.py           # YouTube transcript extraction
│   ├── text.py              # Plain text + HTML-to-markdown
│   ├── pdf.py               # PDF/EPUB via PyMuPDF
│   ├── url/                 # URL extraction engines
│   │   ├── __init__.py      # Engine router + fallback chain
│   │   ├── bs4.py           # BeautifulSoup + readability
│   │   ├── jina.py          # Jina Reader API
│   │   ├── firecrawl.py     # Firecrawl SDK
│   │   └── crawl4ai.py      # Crawl4AI browser automation
│   ├── document/            # Document extraction
│   │   ├── __init__.py      # Document type router
│   │   ├── docx.py          # python-docx
│   │   ├── pptx.py          # python-pptx
│   │   ├── xlsx.py          # openpyxl
│   │   ├── pdf.py           # (imported from parent)
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

Key settings: `url_engine`, `document_engine`, `audio_provider`, `audio_model`, `firecrawl_api_url`, `youtube_languages`, `llm_provider`, `llm_model`

## Code Style

- **Formatting**: PEP 8, enforced by ruff
- **Error handling**: Use custom exceptions from `common/exceptions.py`
- **Tests**: Unit tests for logic, integration tests for file extraction, e2e for network ops

## Release Process

1. Run `make test` to verify everything works
2. Update version in `pyproject.toml`
3. Run `uv sync` to update the lock file
4. Commit changes
5. Merge to main (if in a branch)
6. Tag the release
7. Push to GitHub
