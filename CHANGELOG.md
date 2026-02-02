# Changelog

All notable changes to Content Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - Unreleased

### Added
- **Processor Registry System** - Declarative processor registration with auto-routing
  - New base classes: `Processor`, `ProcessorCapabilities`, `ProcessorResult`, `Source`
  - `ProcessorRegistry` singleton for discovering and selecting processors
  - `@processor()` decorator for registering processors with MIME types, extensions, priority
  - Priority-based selection when multiple processors support the same type
  - Auto-discovery: processors register when imported

- **New Extract API (v2.0)** - Simplified named parameters with backward compatibility
  - New signature: `extract_content(url=..., file_path=..., content=..., engine=..., options=...)`
  - Returns `ExtractionResult` with `content`, `engine_used`, `metadata`, `warnings`
  - Engine fallback chains: `engine=["docling", "pymupdf4llm", "pymupdf"]`
  - Legacy API still supported: `extract_content({"url": "..."})`

- **Registry-Based Routing** - Replaced hardcoded conditionals with registry queries
  - `route_and_extract()` for direct registry-based extraction
  - `detect_mime_type()` for automatic MIME type detection
  - `get_available_engines()` to list all registered processors

- **Modular Benchmark System** - Extensible framework for comparing extraction engines
  - Unified CLI: `uv run python scripts/benchmark.py --type pdf|docx|all`
  - Support for PDF and DOCX benchmarks with quality scoring
  - Pluggable engine architecture (Engine, QualityScorer, ContentAnalyzer base classes)
  - Automatic report generation (Markdown and JSON)
  - Per-file quality scoring against expected content

- **DOCX Extraction Engines** - New engines for Word document extraction
  - `python-docx` engine: Fast, lightweight extraction (0.1s, 7MB)
  - `docling` engine: Full structure preservation with table detection

- **VLM-Powered Document Extraction** - Vision-language model support via Docling
  - Local inference with transformers or MLX (Apple Silicon optimized)
  - Remote inference via docling-serve API
  - Configurable via environment variables or YAML
  - Support for granite-docling and smol-docling models

- **Picture Description** - VLM-based image captioning in documents
  - SmolVLM-256M-Instruct and Granite Vision 3.3-2B models
  - Configurable via `CCORE_DOCLING_DO_PICTURE_DESCRIPTION`
  - CPU inference (MPS produces incorrect output)

- **Unified Docling Options** - Centralized configuration for all Docling settings
  - Environment variables: `CCORE_VLM_*`, `CCORE_DOCLING_*`
  - YAML configuration under `extraction.docling`
  - Per-request overrides via ProcessSourceInput

- **Marker PDF Engine** - Optional GPL-3.0 licensed deep learning extraction
  - High-quality markdown output for complex documents
  - Check `MARKER_AVAILABLE` before using

### Changed
- **PyMuPDF Now Optional** - Default to MIT-licensed Docling for PDF extraction
  - PyMuPDF/pymupdf4llm require explicit installation: `pip install content-core[pymupdf]`
  - Check `PYMUPDF_AVAILABLE` / `PYMUPDF4LLM_AVAILABLE` before using
  - Maintains AGPL-3.0 compliance for users who need MIT-only dependencies

- **Documentation Restructured** - Modular, topic-based documentation
  - Simplified README (~130 lines vs 798)
  - Engine-specific docs: `docs/engines/` (docling, pymupdf, marker, url-engines, etc.)
  - Benchmark results: `docs/benchmarks/`
  - Integration guides: `docs/integrations/` (MCP, Raycast, macOS, LangChain)
  - Legacy docs preserved in `docs/_legacy/`

- **Enhanced Simple PDF Extraction** - Upgraded to use pymupdf4llm when available
  - Better table detection and markdown formatting
  - Quality flags for improved text extraction

### Fixed
- **MLX Backend Selection** - Use `vlm_options=` parameter to preserve inference framework
- **VLM Pipeline Options** - Proper configuration propagation for local/remote modes

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
  - Updated StateGraph API: `input` → `input_schema`, `output` → `output_schema`
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