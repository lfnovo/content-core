# Content Core

Library for extracting, cleaning, and summarizing content from URLs, files, and text.

## Commands

- **Install dependencies**: `uv sync --group dev`
- **Run tests**: `make test` or `uv run pytest -v`
- **Run single test**: `uv run pytest -k "test_name"`
- **Linting**: `make ruff` (runs `ruff check . --fix`)
- **Build package**: `uv build`
- **Run benchmarks**: `uv run python scripts/benchmark.py`

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
│   ├── types.py         # Type aliases (DocumentEngine, UrlEngine, VlmInferenceMode, VlmBackend)
│   └── utils.py         # Input content processing
│
├── processors/          # Format-specific extractors (see processors/CLAUDE.md)
│   ├── __init__.py      # Auto-discovery and exports (ProcessorRegistry, Processor, Source)
│   ├── base.py          # Base classes: Processor, ProcessorCapabilities, ProcessorResult, Source
│   ├── registry.py      # ProcessorRegistry singleton and @processor decorator
│   ├── pdf.py           # PDF/EPUB via PyMuPDF (PyMuPDFProcessor)
│   ├── pdf_llm.py       # PDF via pymupdf4llm (PyMuPDF4LLMProcessor)
│   ├── url.py           # URL extraction (JinaProcessor, FirecrawlProcessor, Crawl4AIProcessor, BS4Processor)
│   ├── audio.py         # Audio transcription (WhisperProcessor)
│   ├── video.py         # Video-to-audio (VideoProcessor)
│   ├── youtube.py       # YouTube transcripts (YouTubeProcessor)
│   ├── office.py        # Office docs (OfficeProcessor)
│   ├── text.py          # Plain text (TextProcessor)
│   ├── docling.py       # Docling integration (DoclingProcessor)
│   ├── docling_vlm.py   # VLM-powered extraction (DoclingVLMProcessor)
│   └── marker.py        # Marker PDF extraction (MarkerProcessor, GPL-3.0)
│
├── content/             # High-level workflows
│   ├── extraction/      # Content extraction
│   │   ├── __init__.py  # extract_content() API (new v2.0 + legacy)
│   │   ├── graph.py     # LangGraph workflow (legacy routing)
│   │   └── router.py    # Registry-based routing (v2.0)
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

scripts/
├── benchmark.py         # Unified benchmark CLI
└── benchmarks/          # Benchmark framework
    ├── base.py          # Abstract classes (Engine, QualityScorer, etc.)
    ├── runner.py        # BenchmarkRunner
    ├── reporter.py      # ReportGenerator
    ├── types/           # Engine implementations by file type
    │   ├── pdf.py       # PDF engines and scorer
    │   └── docx.py      # DOCX engines and scorer
    └── test_data/       # Expected content for quality scoring
        ├── pdf_expected.py
        └── docx_expected.py

docs/
├── getting-started.md   # Quick start guide
├── configuration.md     # All configuration options
├── cli.md               # CLI reference (ccore, cclean, csum)
├── engines/             # Engine-specific documentation
│   ├── overview.md      # Engine comparison and selection
│   ├── docling.md       # Docling (MIT, default)
│   ├── docling-vlm.md   # Docling VLM (MIT)
│   ├── pymupdf.md       # PyMuPDF (AGPL-3.0)
│   ├── marker.md        # Marker (GPL-3.0)
│   ├── url-engines.md   # URL engines (firecrawl, jina, crawl4ai, bs4)
│   └── audio-video.md   # Audio/video transcription
├── benchmarks/          # Performance benchmarks
│   ├── pdf-benchmark.md
│   └── docx-benchmark.md
└── integrations/        # Integration guides
    ├── mcp.md           # Claude Desktop / MCP
    ├── raycast.md       # Raycast extension
    ├── macos.md         # macOS Services
    └── langchain.md     # LangChain tools
```

## Architecture

**Two API modes** (v2.0):

1. **New API** - Named parameters with registry-based routing:
   ```python
   result = await extract_content(url="https://example.com/doc.pdf")
   result = await extract_content(file_path="/path/to/file.pdf", engine="docling")
   result = await extract_content(file_path="/path/to/file.pdf", engine=["docling", "pymupdf"])
   # Returns ExtractionResult
   ```

2. **Legacy API** - Dict/ProcessSourceInput with LangGraph workflow:
   ```python
   result = await extract_content({"url": "https://example.com/doc.pdf"})
   result = await extract_content(ProcessSourceInput(file_path="/path/to/file.pdf"))
   # Returns ProcessSourceOutput
   ```

**Data flow (New API)**: Input -> Router -> Processor Registry -> Processor -> ExtractionResult

**Data flow (Legacy)**: ProcessSourceInput -> LangGraph workflow -> Processor -> ProcessSourceOutput

**Key patterns**:
- **Processor Registry**: Singleton that manages processor discovery by MIME type/extension/priority
- **@processor decorator**: Registers processors with capabilities (MIME types, extensions, priority)
- **Stateless processors**: Each processor class implements `extract(source, options)` -> `ProcessorResult`
- LangGraph StateGraph still used for legacy API and composite workflows (video -> audio -> transcribe)
- Retry decorators handle transient failures for network/API operations
- Configuration loaded from YAML with env var overrides

## Integration

- **Esperanto**: LLM and STT model abstraction via `ModelFactory`
- **LangGraph**: Workflow orchestration in `content/extraction/graph.py`
- **LangChain**: Tool wrappers in `tools/` for agent integration
- **ai-prompter**: Template rendering in `templated_message.py`

## Gotchas

- Import aliases: `content_core.extraction` = `content_core.content.extraction`
- `pymupdf` is optional (AGPL-3.0 license): check `PYMUPDF_AVAILABLE` before using
- `pymupdf4llm` is optional (AGPL-3.0 license): check `PYMUPDF4LLM_AVAILABLE` before using
- Default PDF extraction uses Docling (MIT) when PyMuPDF not installed
- `docling` is optional: check `DOCLING_AVAILABLE` before using
- `docling_vlm` is optional: check `DOCLING_VLM_LOCAL_AVAILABLE` for local inference
- `marker` is optional (GPL-3.0 license): check `MARKER_AVAILABLE` before using
- VLM remote mode requires `httpx`: check `HTTPX_AVAILABLE`
- Proxy must be passed through state or config, not set globally on requests
- All async operations should use retry decorators for resilience
- `ModelFactory` caches models but invalidates on proxy change
- **Picture description**: Use `docling` engine (not `docling-vlm`) with `CCORE_DOCLING_DO_PICTURE_DESCRIPTION=true`. Forces CPU due to MPS issues.

## Benchmarking

Run extraction benchmarks:

```bash
# All types
uv run python scripts/benchmark.py

# PDF only
uv run python scripts/benchmark.py --type pdf --files benchmark.pdf

# DOCX only
uv run python scripts/benchmark.py --type docx --files benchmark.docx

# Specific engines
uv run python scripts/benchmark.py --type pdf --engines docling,docling-vlm
```

Results saved to `tests/output/benchmark_TIMESTAMP/`.

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
