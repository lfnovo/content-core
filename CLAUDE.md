# Content Core

Library for extracting, cleaning, and summarizing content from URLs, files, and text.

## Commands

- **Install dependencies**: `uv sync --group dev`
- **Run tests**: `make test` or `uv run pytest -v`
- **Run single test**: `uv run pytest -k "test_name"`
- **Linting**: `make ruff` (runs `ruff check . --fix`)
- **Build package**: `uv build`
- **Build docs**: `make build-docs`

## Codebase Structure

```
src/content_core/
├── __init__.py          # CLI entry points (ccore, cclean, csum) and public API
├── config.py            # Configuration loading, engine selection, retry/proxy settings
├── models.py            # ModelFactory for Esperanto LLM/STT model caching
├── templated_message.py # LLM prompt execution with Jinja templates
├── logging.py           # Loguru configuration
│
├── common/              # Shared infrastructure (see common/CLAUDE.md)
│   ├── exceptions.py    # Exception hierarchy
│   ├── retry.py         # Retry decorators for transient failures
│   ├── state.py         # Pydantic state models for LangGraph
│   ├── types.py         # Type aliases (DocumentEngine, UrlEngine)
│   └── utils.py         # Input content processing
│
├── processors/          # Format-specific extractors (see processors/CLAUDE.md)
│   ├── pdf.py           # PDF/EPUB via PyMuPDF
│   ├── url.py           # URL extraction (jina/firecrawl/crawl4ai/bs4)
│   ├── audio.py         # Audio transcription via Esperanto STT
│   ├── video.py         # Video-to-audio via moviepy
│   ├── youtube.py       # YouTube transcript extraction
│   ├── office.py        # Office docs (docx/pptx/xlsx)
│   ├── text.py          # Plain text files
│   └── docling.py       # Optional Docling integration
│
├── content/             # High-level workflows
│   ├── extraction/      # LangGraph extraction workflow
│   │   └── graph.py     # Main extraction state graph
│   ├── identification/  # File type detection
│   │   └── file_detector.py
│   ├── cleanup/         # Content cleaning via LLM
│   └── summary/         # Content summarization via LLM
│
├── tools/               # LangChain tool wrappers (see tools/CLAUDE.md)
│   ├── extract.py       # extract_content_tool
│   ├── cleanup.py       # cleanup_content_tool
│   └── summarize.py     # summarize_content_tool
│
└── mcp/                 # MCP server for AI assistant integration
    └── server.py        # FastMCP server implementation
```

## Architecture

**Data flow**: Input -> LangGraph workflow -> Processor -> Output

1. `ProcessSourceInput` received via API or CLI
2. `content/extraction/graph.py` routes to appropriate processor based on source type
3. Processor extracts content and returns state updates
4. `ProcessSourceOutput` returned to caller

**Key patterns**:
- LangGraph StateGraph orchestrates extraction workflow
- Processors are stateless functions that take `ProcessSourceState` and return dict updates
- Retry decorators handle transient failures for network/API operations
- Configuration loaded from YAML with env var overrides

## Integration

- **Esperanto**: LLM and STT model abstraction via `ModelFactory`
- **LangGraph**: Workflow orchestration in `content/extraction/graph.py`
- **LangChain**: Tool wrappers in `tools/` for agent integration
- **ai-prompter**: Template rendering in `templated_message.py`

## Gotchas

- Import aliases: `content_core.extraction` = `content_core.content.extraction`
- `docling` is optional: check `DOCLING_AVAILABLE` before using
- Proxy must be passed through state or config, not set globally on requests
- All async operations should use retry decorators for resilience
- `ModelFactory` caches models but invalidates on proxy change

## Code Style

- **Formatting**: Follow PEP 8
- **Imports**: Organize by standard library, third-party, local
- **Error handling**: Use custom exceptions from `common/exceptions.py`
- **Documentation**: Update docs when changing functionality
- **Tests**: Write unit tests for new code; integration tests for workflows

## Release Process

1. Run `make test` to verify everything works
2. Update version in `pyproject.toml`
3. Run `uv sync` to update the lock file
4. Commit changes
5. Merge to main (if in a branch)
6. Tag the release
7. Push to GitHub
