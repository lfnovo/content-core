# Content Core v2.0 — Architecture Refactor

This document captures the full architectural review of content-core v1.14.1 and proposes the design for v2.0, a major release that simplifies the project across every layer.

The guiding principle: **content-core does something simple — detect input type, route to the right processor, return content.** The infrastructure should reflect that simplicity.

**Scope change for v2.0**: The `clean`/`cleanup` functionality is being removed entirely. v2.0 will have two core operations: `extract` and `summarize`.

---

## Part 1: Problems Identified

### 1.1 LangGraph is unnecessary

The extraction workflow uses LangGraph (`StateGraph`) to orchestrate what is fundamentally a linear pipeline with conditional branching. The graph definition in `content/extraction/graph.py` (~256 lines) registers 13 nodes, wires conditional edges via string-keyed dicts, and compiles a state machine.

**What LangGraph provides that we don't use:**
- No cycles or loops
- No human-in-the-loop
- No checkpointing or persistence
- No parallelism between nodes
- No streaming of intermediate state
- No subgraphs

**What it costs:**
- A heavy dependency (`langgraph` + transitive `langchain-core`)
- State is implicit (Pydantic models passed through nodes) instead of explicit local variables
- The graph definition (70+ lines of `add_node`/`add_edge`/`add_conditional_edges`) is harder to read than equivalent Python control flow
- MIME-type-to-node routing via string dicts is fragile — a typo in a node name is a silent runtime error
- Debugging requires understanding LangGraph's execution model rather than just stepping through Python

**The entire workflow can be replaced by a single async function of ~60 lines.**

### 1.2 Configuration is overengineered and inconsistent

The configuration system spans 463 lines in `config.py`, two YAML files (`cc_config.yaml` and `models_config.yaml` that are merged at load time), environment variables, and a mutable global dict.

**Three sources with inconsistent priority:**
- For engines: `ProcessSourceState` field > env var > YAML > hardcoded default
- For timeouts: YAML > env var (inverted — env var is explicitly a *fallback*, not an override)
- For retry: env var > YAML > hardcoded default

**Specific issues:**
- ~200 lines of copy-pasted `try/except ValueError` + `logger.warning` for env var parsing (repeated 8+ times)
- `CONFIG` is a mutable global dict with `set_*()` functions that mutate it — stateful, hard to test, prone to race conditions in async
- `get_retry_config()` is 100+ lines for what could be a dict lookup with a fallback
- Two YAML files that get merged at load time add complexity without benefit
- 99% of users will never change retry parameters — hardcoded defaults are sufficient

### 1.3 MCP Server is incomplete

The MCP server (`mcp/server.py`, 215 lines) exposes only 1 of the 3 core functionalities — extraction. Cleanup and summarize are missing despite being ready in the library.

**Other issues:**
- `sys.path.insert(0, ...)` hack for imports (unnecessary if the package is installed properly)
- `suppress_stdout` context manager is fragile — redirects `sys.stdout` to `StringIO`, but C-level output (ffmpeg, fitz) bypasses this entirely
- Security check at lines 90-102 calls `path.resolve()` but never validates the result — the comment "you might want to add additional checks" says it all
- Response format is verbose with metadata (timestamps, extraction_time_seconds) that LLMs consuming the tool don't need
- `datetime.utcnow()` is deprecated since Python 3.12
- No configuration options exposed — users can't choose engine, pass context for summarization, etc.

### 1.4 CLI has bugs and lives in the wrong place

All CLI logic (~140 lines of argparse, wrappers, and parsing) lives in `__init__.py`, meaning it's loaded on every `import content_core`.

**Bugs:**
- **Double extraction in `ccore`**: `process_input_content(content)` at line 109 may extract from a URL, then line 112 calls `extract_content(ProcessSourceInput(content=content))` again with the result. URLs get extracted twice.
- **Naive URL detection**: `"http" in content` matches strings like `"I visited http://example.com yesterday"`.

**Design issues:**
- Three separate binaries (`ccore`, `cclean`, `csum`) instead of subcommands of a single CLI
- This forces `uvx --from content-core ccore "..."` because the binary name doesn't match the package name
- Copy-pasted pattern across all three commands with minimal variation
- `parse_content_format` is called in `cclean`/`csum` but not in `ccore` — inconsistent
- Raw argparse is verbose; modern alternatives (click, typer) would reduce code significantly

### 1.5 Processors are poorly structured

**`url.py` is a monolith with 4 engines (322 lines):**
BS4, Jina, Firecrawl, and Crawl4AI all live in one file. Each has its own patterns (Jina parses text with `startswith("Title:")`, Firecrawl uses an SDK, Crawl4AI needs `ProxyConfig`), but they're mixed together. Adding a new engine means editing a file with 4 existing responsibilities.

**Routing logic is split between two layers:**
`url_provider` (MIME type detection via HEAD request) lives in `url.py`, but the decision of what to do with the result lives in `graph.py` via `url_type_router`. Two layers making related decisions.

**`office.py` extracts content twice:**
`extract_office_content` calls `extract_docx_content_detailed` and then `get_docx_info`, but `get_docx_info` internally calls `extract_docx_content_detailed` again. Same for PPTX and XLSX. Every Office document is processed twice.

**`docling.py` breaks the processor contract:**
All processors return `dict` with state updates. But `extract_with_docling` returns `ProcessSourceState` and mutates the state directly (`state.content = output`, `state.metadata["docling_format"] = fmt`). It's the only processor that does this.

**`video.py` and `audio.py` are an implicit pipeline:**
`video.py` extracts audio and returns `{"file_path": ..., "identified_type": "audio/mp3"}`. The graph knows to chain it to `audio.py` via `workflow.add_edge(...)`. Reading `video.py` alone, you can't tell it's only half the pipeline.

**No common interface:**
Each processor is an async function taking `ProcessSourceState` and returning `dict` — but this is convention, not contract. No base class, Protocol, or enforced type hint. Docling already violates the convention.

### 1.6 Test suite has critical coverage gaps

**176 tests across 11 files, but coverage is highly uneven:**

| Area | Coverage | Quality |
|------|----------|---------|
| Config (env vars, engines, fallbacks) | ~90% | Excellent |
| Retry decorators | ~85% | Excellent |
| File detection | ~80% | Good |
| Audio (concurrency, model override) | ~60% | Good |
| PDF (OCR only) | ~40% | Partial |
| Docling | ~20% | Minimal (mocks only) |
| YouTube, URL, Video, Office, Text | ~5% | Only integration smoke tests |

**Structural problems:**
- No separation between unit/integration/e2e — everything runs together
- Integration tests (`test_extraction.py`, `test_cli.py`) make real network calls and depend on API keys — flaky by nature
- `test_pymupdf_ocr.py` mixes pure function tests with real PDF extraction in the same file
- `pytest.mark.parametrize` is used only once in the entire suite
- Some tests mutate the global `CONFIG` dict and rely on fixture cleanup that can fail
- Assertions like `assert "AI" in result.content` depend on external content not changing
- Tests aren't useful as a feedback tool for AI-assisted development because they're slow, flaky, and don't cover enough

---

## Part 2: Design for v2.0

### 2.1 Replace LangGraph with plain async Python

Remove the `langgraph` dependency entirely. Replace the state graph with a single orchestrator function.

```python
# content_core/extraction.py

async def extract_content(
    input: ProcessSourceInput,
    config: ContentCoreConfig | None = None,
) -> ProcessSourceOutput:
    """Main extraction entry point."""
    cfg = config or get_default_config()

    # 1. Identify source type
    if input.content:
        return await _extract_text(input.content)
    elif input.file_path:
        return await _extract_file(input.file_path, cfg)
    elif input.url:
        return await _extract_url(input.url, cfg)
    else:
        raise InvalidInputError("No source provided")


async def _extract_url(url: str, cfg: ContentCoreConfig) -> ProcessSourceOutput:
    """Route URL to the appropriate processor."""
    if is_youtube_url(url):
        return await youtube.extract(url, cfg)

    mime = await detect_remote_mime(url)

    if mime in DOWNLOADABLE_TYPES:
        tmp_path = await download_file(url)
        try:
            return await _extract_file(tmp_path, cfg)
        finally:
            os.unlink(tmp_path)

    return await url_engines.extract(url, cfg)


async def _extract_file(path: str, cfg: ContentCoreConfig) -> ProcessSourceOutput:
    """Route file to the appropriate processor."""
    mime = await detect_file_type(path)

    if cfg.document_engine == "docling" or (cfg.document_engine == "auto" and mime in DOCLING_SUPPORTED):
        return await docling.extract(path, cfg)
    if mime in PDF_TYPES:
        return await pdf.extract(path)
    if mime in OFFICE_TYPES:
        return await office.extract(path, mime)
    if mime.startswith("video/"):
        return await media.extract_video(path, cfg)
    if mime.startswith("audio/"):
        return await media.extract_audio(path, cfg)
    if mime == "text/plain":
        return await text.extract(path)

    raise UnsupportedTypeException(f"Unsupported file type: {mime}")
```

**What changes:**
- No graph, no nodes, no edges — just Python control flow
- Config is passed explicitly as a parameter, not read from globals
- Each processor returns `ProcessSourceOutput` directly (not dict updates to implicit state)
- The video→audio pipeline is explicit in `media.extract_video`, not implicit in graph edges
- File cleanup (temp downloads) is explicit with `try/finally`

**What stays the same:**
- Processors are still async functions
- `ProcessSourceInput` and `ProcessSourceOutput` Pydantic models remain as the public API
- Retry decorators continue to wrap internal network calls

### 2.2 Simplify configuration with Pydantic

Replace the YAML files + env vars + global dict with a single Pydantic model.

```python
# content_core/config.py

from pydantic import Field
from pydantic_settings import BaseSettings


class ContentCoreConfig(BaseSettings):
    """Content Core configuration.

    Priority: constructor args > environment variables > defaults.
    """

    model_config = SettingsConfigDict(env_prefix="CCORE_")

    # Engine selection
    document_engine: str = "auto"       # auto | simple | docling
    url_engine: str = "auto"            # auto | simple | firecrawl | jina | crawl4ai

    # Audio
    audio_provider: str | None = None    # e.g. "openai", "google"
    audio_model: str | None = None       # e.g. "whisper-1"
    audio_concurrency: int = Field(default=3, ge=1, le=10)

    # Firecrawl
    firecrawl_api_url: str = "https://api.firecrawl.dev"

    # LLM models (for cleanup/summarize)
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    cleanup_model: str | None = None     # Falls back to llm_model
    summary_model: str | None = None     # Falls back to llm_model

    # STT model
    stt_provider: str = "openai"
    stt_model: str = "gpt-4o-transcribe-diarize"

    # YouTube
    youtube_languages: list[str] = ["en", "es", "pt"]


# Singleton for convenience — but never required
_default_config: ContentCoreConfig | None = None


def get_default_config() -> ContentCoreConfig:
    global _default_config
    if _default_config is None:
        _default_config = ContentCoreConfig()
    return _default_config
```

**What this gives us:**
- One source of truth with clear, consistent priority: constructor > env var > default
- Validation built-in via Pydantic (type checking, ranges, allowed values)
- No YAML files to ship, merge, or document
- No mutable global dict — config is immutable once created
- Easy to use programmatically: `ContentCoreConfig(url_engine="firecrawl")`
- Easy to use via env vars: `CCORE_URL_ENGINE=firecrawl` (automatic with `pydantic-settings`)
- Easy to test: just pass a config instance, no patching globals
- ~50 lines instead of 463

**Retry config stays as hardcoded defaults** — they're sensible values that 99% of users never change. If someone needs to customize retry behavior, they can subclass or pass tenacity kwargs.

**YAML support can be added later** as an optional loader that creates a `ContentCoreConfig` from a file. But it's not the primary mechanism.

### 2.3 Restructure processors as self-contained modules

Each processor or engine group becomes its own module with a consistent interface.

```
src/content_core/
├── processors/
│   ├── __init__.py          # Processor Protocol definition
│   ├── url/
│   │   ├── __init__.py      # URL engine router + fallback chain
│   │   ├── bs4.py           # BeautifulSoup + readability
│   │   ├── jina.py          # Jina Reader API
│   │   ├── firecrawl.py     # Firecrawl SDK
│   │   └── crawl4ai.py      # Crawl4AI browser automation
│   ├── document/
│   │   ├── __init__.py      # Document type router
│   │   ├── pdf.py           # PyMuPDF extraction
│   │   ├── docx.py          # python-docx
│   │   ├── pptx.py          # python-pptx
│   │   ├── xlsx.py          # openpyxl
│   │   └── docling.py       # Optional Docling integration
│   ├── media/
│   │   ├── __init__.py      # Video+audio pipeline (explicit)
│   │   ├── audio.py         # Transcription via Esperanto STT
│   │   └── video.py         # Video-to-audio extraction
│   ├── youtube.py           # YouTube transcript extraction
│   └── text.py              # Plain text + HTML-to-markdown
```

**Common interface via Protocol:**

```python
# processors/__init__.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class Processor(Protocol):
    async def extract(self, source: str, config: ContentCoreConfig) -> ProcessSourceOutput:
        ...
```

**Key changes:**
- URL engines are individual files — adding a new engine means adding a new file, not editing a 322-line monolith
- `url/__init__.py` handles engine selection and fallback chain
- Office documents are individual files — no more double extraction
- `media/__init__.py` makes the video→audio pipeline explicit
- `docling.py` follows the same interface as everything else
- Each module is self-contained: its dependencies, its retry logic, its error handling

### 2.4 Unified CLI with subcommands

Replace three separate binaries with one CLI using subcommands.

```
content-core extract <source> [--engine ENGINE] [--format FORMAT]
content-core clean [source] [--context CONTEXT]
content-core summarize [source] [--context CONTEXT]
content-core mcp                  # Start MCP server
```

**Usage with uvx becomes simple:**
```bash
# No --from needed — package name = command name
uvx content-core extract "https://example.com"
uvx content-core clean "some text"
uvx content-core extract "https://example.com" | uvx content-core summarize
```

**Implementation with click or typer:**

```python
# content_core/cli.py
import click

@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug):
    """Content Core — Extract, clean, and summarize content."""
    if debug:
        configure_logging(debug=True)

@cli.command()
@click.argument("source")
@click.option("-f", "--format", type=click.Choice(["text", "json", "xml"]), default="text")
@click.option("--engine", default=None, help="Override extraction engine")
def extract(source, format, engine):
    """Extract content from a URL, file, or text."""
    ...

@cli.command()
@click.argument("content", required=False)
@click.option("--context", default="", help="Context for processing")
def clean(content, context):
    """Clean content using LLM."""
    ...

@cli.command()
@click.argument("content", required=False)
@click.option("--context", default="", help="Context for summarization")
def summarize(content, context):
    """Summarize content using LLM."""
    ...

@cli.command()
def mcp():
    """Start the MCP server."""
    ...
```

**pyproject.toml:**
```toml
[project.scripts]
content-core = "content_core.cli:cli"
```

**What changes:**
- Single entry point, discoverable via `content-core --help`
- `uvx content-core` works without `--from`
- CLI code moves out of `__init__.py`
- No more double extraction bug
- Pipe-friendly: each command reads stdin naturally
- `--engine` flag allows per-invocation override

### 2.5 Complete the MCP Server

Expose all three core operations and add configuration options.

```python
# content_core/mcp/server.py

@mcp.tool
async def extract_content(
    url: str | None = None,
    file_path: str | None = None,
    engine: str | None = None,
) -> str:
    """Extract content from a URL or file. Returns the extracted text content."""
    config = ContentCoreConfig(url_engine=engine) if engine else None
    ...
    return result.content

@mcp.tool
async def clean_content(content: str) -> str:
    """Clean and normalize extracted content using LLM."""
    return await cleanup_content(content)

@mcp.tool
async def summarize_content(
    content: str,
    context: str = "",
) -> str:
    """Summarize content using LLM with optional context."""
    return await summarize(content, context)
```

**What changes:**
- All 3 tools exposed (not just extract)
- Return plain text, not verbose JSON dicts with metadata — LLMs work better with simple responses
- Engine selection exposed as a parameter
- No `sys.path.insert` hack
- No `suppress_stdout` hack — handle MoviePy/ffmpeg output properly via logging config
- Remove the fake security check

### 2.6 Test strategy: three tiers with clear purpose

```
tests/
├── unit/                          # Fast, no I/O, no network — AI agent feedback loop
│   ├── test_routing.py            # Input → correct processor selection
│   ├── test_config.py             # Config creation, validation, env var loading
│   ├── test_url_engine_select.py  # URL engine selection + fallback logic
│   ├── test_doc_engine_select.py  # Document engine selection + fallback logic
│   ├── test_file_detection.py     # MIME type detection from file signatures
│   ├── test_youtube_parsing.py    # Video ID extraction, transcript formatting
│   ├── test_pdf_cleaning.py       # PDF text cleaning, table conversion
│   ├── test_office_extraction.py  # DOCX/PPTX/XLSX parsing (mocked I/O)
│   ├── test_text_processing.py    # HTML detection, markdown conversion
│   └── test_audio_pipeline.py     # Segmentation logic, concurrency, model selection
│
├── integration/                   # Local I/O, no network — CI on every commit
│   ├── test_file_extraction.py    # Real files from tests/fixtures/
│   ├── test_cli.py                # CLI subcommands with mocked processors
│   └── test_mcp.py                # MCP tool interface validation
│
├── e2e/                           # Network, API keys — pre-release gate
│   ├── test_url_engines.py        # Firecrawl, Jina, Crawl4AI with real URLs
│   ├── test_youtube.py            # Real transcript extraction
│   └── test_pipeline.py           # Extract → Clean → Summarize end-to-end
│
├── fixtures/                      # Test data files
│   ├── sample.pdf
│   ├── sample.docx
│   ├── sample.pptx
│   ├── sample.xlsx
│   └── sample.mp3
│
└── conftest.py                    # Shared fixtures, markers
```

**Pytest markers:**
```ini
[tool.pytest.ini_options]
markers = [
    "e2e: end-to-end tests requiring network and API keys",
]
```

**Commands:**
```bash
make test          # unit + integration (seconds, used by AI agents)
make test-e2e      # e2e only (pre-release)
make test-all      # everything
```

**Design principles for AI-agent-friendly tests:**
- **Fast**: unit + integration runs in seconds, not minutes
- **Deterministic**: no network calls, no external state
- **Granular**: `pytest -k pdf` gives confidence about PDF changes
- **Self-documenting**: test names describe intended behavior, not implementation

---

## Part 3: Migration plan

### Phase 1: Foundation (no breaking changes yet)

1. **Create `ContentCoreConfig` Pydantic model** alongside existing config system
2. **Create processor Protocol** and adapt existing processors to conform
3. **Add unit tests** for routing logic, engine selection, and processors
4. **Move CLI code** from `__init__.py` to `cli.py` (keep old entry points as aliases)
5. **Set up test tiers** (unit/integration/e2e markers and directory structure)

### Phase 2: Core refactor

6. **Replace LangGraph** with plain async orchestrator function
   - Remove `content/extraction/graph.py`
   - Create `extraction.py` with direct routing
   - Remove `langgraph` dependency
7. **Restructure processors** into sub-packages (url/, document/, media/)
   - Split `url.py` into individual engine files
   - Split `office.py` into individual format files (fix double extraction)
   - Make video→audio pipeline explicit in `media/`
   - Fix docling to follow processor Protocol
8. **Replace config system** with `ContentCoreConfig`
   - Remove YAML files
   - Remove `set_*()` global mutators
   - Remove `CONFIG` global dict
   - Add `pydantic-settings` dependency

### Phase 3: User-facing changes

9. **Unified CLI** with subcommands via click/typer
   - Single `content-core` command
   - Remove `ccore`, `cclean`, `csum` binaries
10. **Complete MCP server** with all 3 tools + config options
11. **Update public API** in `__init__.py` — clean exports only
12. **Update documentation** — README, CLAUDE.md, CHANGELOG

### Phase 4: Cleanup

13. **Remove dead code** — old config functions, graph.py, LangGraph state models
14. **Remove unnecessary dependencies** — `langgraph`, `pyyaml` (if YAML support dropped), `dicttoxml` (if XML output dropped)
15. **Final test pass** — full e2e suite before release
16. **Tag v2.0.0**

---

## Part 4: Dependency changes

### Removed
- `langgraph` — replaced by plain async Python
- `pyyaml` — configuration via Pydantic, not YAML (optional: keep as extra if YAML config loading desired)
- `dicttoxml` — evaluate if XML output format is still needed in CLI

### Added
- `pydantic-settings` — environment variable loading for config
- `click` or `typer` — CLI framework (replaces raw argparse)

### Kept
All processor dependencies remain unchanged (aiohttp, bs4, pymupdf, esperanto, moviepy, etc.)

---

## Part 5: Public API for v2.0

```python
import content_core

# Extract
result = await content_core.extract("https://example.com")
result = await content_core.extract("/path/to/file.pdf")
result = await content_core.extract(content="some text to process")

# With config override
from content_core import ContentCoreConfig
config = ContentCoreConfig(url_engine="firecrawl", audio_provider="google")
result = await content_core.extract("https://example.com", config=config)

# Clean
cleaned = await content_core.clean("messy text here")

# Summarize
summary = await content_core.summarize("long text here", context="explain to a child")
```

**CLI:**
```bash
content-core extract "https://example.com"
content-core extract document.pdf --format json
content-core clean "messy text"
content-core summarize "long text" --context "bullet points"
echo "text" | content-core clean
content-core extract "https://example.com" | content-core summarize
content-core mcp
```

**MCP:**
Three tools: `extract_content`, `clean_content`, `summarize_content` — all returning plain text.
