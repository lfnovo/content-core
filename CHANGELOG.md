# Changelog

All notable changes to Content Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-04-11

### Added
- Docling enrichment flags: `docling_ocr`, `docling_formulas`, `docling_vision` for controlling OCR, formula extraction, and image/chart processing
- `ContentCoreConfig` based on pydantic-settings with `CCORE_` environment variable prefix for all configuration
- Unified CLI command `content-core` with subcommands: `extract`, `summarize`, `mcp`
- `summarize_content` MCP tool for text summarization directly in Claude Desktop
- New configuration fields: `CCORE_LLM_PROVIDER`, `CCORE_LLM_MODEL`, `CCORE_STT_PROVIDER`, `CCORE_STT_MODEL`, `CCORE_STT_TIMEOUT`, `CCORE_YOUTUBE_LANGUAGES`
- Reddit post extraction via public JSON endpoint (#35) — extracts post content and comments, with fallback to normal URL extraction
- Firecrawl `proxy` and `wait_for` options (#34) — defaults to `auto` proxy and 3000ms wait for better out-of-the-box extraction
- CLI `--engine` flag routes automatically to `url_engine` or `document_engine` based on input type
- Persistent config file at `~/.content-core/config.toml` with CLI management (`config list`, `config set`, `config delete`)
- Configuration priority: constructor args > env vars (`CCORE_*`) > config file > defaults
- New EPUB processor using fast-ebook (MIT, Rust-powered) for EPUB extraction

### Changed
- **Breaking**: `extract_content()` now uses keyword-only arguments instead of `ExtractionInput`/dict positional parameter:
  ```python
  # Before
  await extract_content({"url": "https://example.com"})
  await extract_content(ExtractionInput(file_path="doc.pdf"))

  # After
  await extract_content(url="https://example.com")
  await extract_content(file_path="doc.pdf")
  ```
- **Breaking**: Engine overrides are now passed via `ContentCoreConfig` instead of input dict:
  ```python
  # Before
  await extract_content({"url": "...", "url_engine": "firecrawl"})

  # After
  config = ContentCoreConfig(url_engine="firecrawl")
  await extract_content(url="...", config=config)
  ```
- Bumped Docling optional dependency to >=2.86.0
- Replaced PyMuPDF (AGPL3) with pdfplumber (MIT) for PDF extraction
- EPUB extraction now uses fast-ebook (MIT) instead of PyMuPDF — separate `processors/document/epub.py` processor
- Replaced moviepy with direct ffmpeg/ffprobe calls for audio processing — faster (stream copy, no re-encoding), fixes chapter metadata parsing bug (#33)
- Replaced LangGraph orchestration with plain async Python orchestrator in `extraction.py`
- Restructured processors into `url/` (bs4, jina, firecrawl, crawl4ai), `document/` (docx, pptx, xlsx, docling), and `media/` (audio, video)
- MCP server now returns plain text instead of structured JSON
- MCP server invoked via `content-core mcp` instead of `content-core-mcp`
- Public API simplified to `content_core.extract_content()`, `content_core.summarize()`, `content_core.ContentCoreConfig`
- Configuration uses pydantic-settings instead of YAML files and `CONFIG` dict
- `langchain-core` moved to optional dependency (`pip install content-core[langchain]`)

### Removed
- LangGraph dependency and state graph workflow
- YAML configuration files (`cc_config.yaml`, `models_config.yaml`)
- `CONFIG` dict and `set_*()` configuration functions
- Cleanup/clean functionality (`clean()`, `cleanup_content()`, `cclean` CLI command)
- Old CLI entry points: `ccore`, `cclean`, `csum`
- Raycast extension
- macOS Services integration
- `ExtractionInput` as required parameter (model still available for internal use)
- PyMuPDF dependency (AGPL3 license)
- moviepy dependency (replaced with direct ffmpeg/ffprobe calls)
- `pymupdf_enable_formula_ocr`, `pymupdf_formula_threshold`, `pymupdf_ocr_fallback` config fields and `CCORE_PYMUPDF_*` environment variables
- Built-in OCR support for formula-heavy PDFs (was disabled by default)

### Fixed
- Audio processing crashes on MP3 files with chapter metadata (#33) — replaced moviepy with direct ffmpeg calls
- Firecrawl API URL now uses `FIRECRAWL_API_URL` env var (#13) — consistent with `FIRECRAWL_API_KEY` naming convention
- MCP `engine` parameter now correctly routes to `document_engine` for file inputs
- Office documents (DOCX, PPTX, XLSX) no longer extracted twice in certain conditions
- Docling processor returns correct type consistently

## [1.14.1] - 2026-01-29

### Fixed
- **YouTube Transcript Extraction** - Updated to youtube-transcript-api v1.0+ API
  - The library removed deprecated static methods (`list_transcripts`, `get_transcript`) in v1.0
  - Now uses instance-based API: `YouTubeTranscriptApi().list()` and `.fetch()`
  - Restored youtube-transcript-api as primary engine with pytubefix as fallback
- **Video Processor Error Handling** - Fixed LangGraph compatibility issue
  - Video extraction now returns proper dict on error instead of `False`
  - Prevents `InvalidUpdateError: Expected dict, got False` when ffprobe is missing

## [1.14.0] - 2026-01-29

### Changed
- **Simplified Proxy Configuration** - Removed custom proxy infrastructure in favor of standard environment variables
  - Now uses standard `HTTP_PROXY` / `HTTPS_PROXY` environment variables (same as most HTTP clients)
  - Removed custom `CCORE_HTTP_PROXY` environment variable
  - Removed `proxy` field from `ProcessSourceInput` and `ProcessSourceState`
  - Removed programmatic API: `set_proxy()`, `clear_proxy()`, `get_proxy()`, `get_no_proxy()`
  - Removed proxy section from YAML configuration
  - All HTTP clients (aiohttp) now use `trust_env=True` to automatically read proxy settings
  - Crawl4AI bridges `HTTP_PROXY` to its `ProxyConfig` for consistent behavior
  - Aligns with Esperanto library's proxy handling approach

### Removed
- `proxy` parameter from extraction API
- Custom proxy configuration functions from `content_core.config`
- Proxy-related unit and integration tests (proxy now handled by underlying HTTP clients)

## [1.13.0] - 2026-01-25

### Added
- **HTML to Markdown Conversion** - Auto-detect and convert HTML content to markdown
  - Detects HTML structure in text content (headings, paragraphs, lists, links, code, etc.)
  - Uses `markdownify` library for deterministic conversion
  - Useful for processing "rendered markdown" copied from preview panes (VS Code, Obsidian reading mode, browsers)
  - Plain text without HTML passes through unchanged
  - New exports in `processors/text.py`: `process_text_content`, `detect_html`

## [1.12.0] - 2026-01-25

### Changed
- **LangGraph v1 Migration** - Updated to LangGraph v1.0+ (from v0.3.x)
  - Minimum requirement now `langgraph>=1.0.0`
  - Updated StateGraph API: `input` -> `input_schema`, `output` -> `output_schema`
  - No breaking changes for users - same API surface maintained

## [1.11.0] - 2026-01-25

### Added
- **Self-Hosted Firecrawl Support** - Configure a custom Firecrawl API URL for self-hosted instances
  - Environment variable: `FIRECRAWL_API_BASE_URL`
  - YAML config: `extraction.firecrawl.api_url`
  - Programmatic API: `set_firecrawl_api_url()`, `get_firecrawl_api_url()`
  - Debug logging when using a custom base URL
  - Documentation with link to [Firecrawl self-hosting guide](https://github.com/mendableai/firecrawl/blob/main/SELF_HOST.md)

## [1.10.0] - 2026-01-16

### Added
- **HTTP/HTTPS Proxy Support** - Route all network requests through a configured proxy
  - 4-level configuration priority: Per-request > Programmatic > Environment variable > YAML config
  - Environment variables: `CCORE_HTTP_PROXY`, `HTTP_PROXY`, `HTTPS_PROXY`
  - Programmatic API: `set_proxy()`, `clear_proxy()`, `get_proxy()`
  - Per-request override via `proxy` parameter in `ProcessSourceState`
  - Bypass list support via `NO_PROXY` environment variable
  - Full proxy support for: aiohttp requests, Esperanto LLM/STT models, Crawl4AI, pytubefix, youtube-transcript-api
  - Warning logged when using Firecrawl (no client-side proxy support)
- Pure Python file type detection via the new `FileDetector` class
- Comprehensive file signature detection for 25+ file formats
- Smart detection for ZIP-based formats (DOCX, XLSX, PPTX, EPUB)
- Custom audio model configuration - override speech-to-text provider and model at runtime
  - Pass `audio_provider` and `audio_model` parameters through `extract_content()` API
  - Supports any provider/model combination available through Esperanto library
  - Maintains full backward compatibility - existing code works unchanged
  - Includes validation with helpful warnings and error messages

### Changed
- File type detection now uses pure Python implementation instead of libmagic
- Improved cross-platform compatibility - no system dependencies required

### Removed
- Dependency on `python-magic` and `python-magic-bin`
- System requirement for libmagic library

### Technical Details
- New proxy configuration module in `content_core/config.py`
- Proxy support integrated into all network-making components
- Replaced libmagic dependency with custom `FileDetector` implementation
- File detection based on binary signatures and content analysis
- Maintains same API surface - no breaking changes for users
- Significantly simplified installation process across all platforms

## Previous Releases

For releases prior to this changelog, please see the [GitHub releases page](https://github.com/lfnovo/content-core/releases).
