# Changelog

All notable changes to Content Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-09-06

### Added
- Local HTML file ingestion through the simple engine, including `.html`/`.htm` routing, HTML-to-Markdown conversion, document titles, minimal HTML documents, BOMs and legacy character encodings (#59, #66).
- Public exception exports from `content_core`: `ContentCoreError`, `UnsupportedTypeException`, `InvalidInputError`, `ConfigurationError`, `NotFoundError`, `NoTranscriptFound`, `NetworkError`, `ExternalServiceError` and `FileOperationError` (#50, #52). Typed failures can be caught through the public API. Some existing failures still escape as untyped exceptions until #60; exporting the taxonomy does not complete that migration.

### Changed
- PyPI publication starts when a GitHub Release is published, including publishing a draft. Creating or pushing a tag alone no longer publishes. The packaging gate verifies that the release tag matches the package version.
- Library imports no longer configure process-wide Loguru handlers. Content Core logging is disabled by default for library consumers; use `logger.enable("content_core")` with the host application's handlers, or `content_core.configure_logging()` from an application entry point. CLI and MCP entry points configure their own stderr logging and honor debug settings (#47).
- Published wheel and sdist now come directly from the artifacts validated by the publishing workflow's packaging job, rather than being rebuilt in the upload job (#57).

### Removed
- Unused `asciidoc` dependency (#58).
- Unused internal `Processor` Protocol; processor contracts remain documented in `ARCHITECTURE.md` (#53).
- Unused internal exception classes `DatabaseOperationError`, `AuthenticationError` and `RateLimitError` (#52). None had a raise site; direct imports from `content_core.common.exceptions` must be updated. The replacement taxonomy is public, but provider error wrapping is still incomplete pending #60.

### Fixed
- Explicit `document_engine="docling"` now raises `ConfigurationError` when the optional engine is unavailable, instead of silently using the simple engine. The error names `pip install "content-core[docling]"` and the `CCORE_DOCUMENT_ENGINE=simple` alternative. `auto` still permits fallback, and `check_file_support` returns an unsupported verdict with the reason (#50).
- Invalid engine names are rejected at configuration entry points, including constructor arguments, environment variables, TOML files and `content-core config set`. Misspelled boolean values are also rejected before writing; CLI/MCP validate engine names for the input type (#51).
- MCP `serverInfo.version` reports the installed Content Core version instead of FastMCP's version (#56).

### Documentation
- Documented Firecrawl-compatible backends through `FIRECRAWL_API_URL` (#86).

## [2.0.7] - 2026-09-02

### Added
- `crawl4ai_api_token` setting (env var `CRAWL4AI_API_TOKEN`, mirroring `CRAWL4AI_API_URL`) for the Crawl4AI Docker API (#80)

### Fixed
- Video extraction wrote its intermediate `<name>_audio.mp3` next to the user's source video and deleted it afterwards (#74), silently destroying a pre-existing file of that name, failing on read-only source directories, and colliding across concurrent extractions. The intermediate now lives in a temporary directory, mirroring audio transcription
- Crawl4AI Docker mode was rejected by any Crawl4AI >= 0.9.0 instance (#80): the client posted to `/crawl` with no `Authorization` header, and recent versions require a bearer token for external connections by default. The token is now sent as `Authorization: Bearer <token>` when configured; unset keeps the previous unauthenticated behavior

## [2.0.6] - 2026-07-30

### Fixed
- `.opus` audio still failed on 2.0.5, one step later in the pipeline (#69): OpenAI validates transcription uploads by filename extension and rejects `opus` while accepting `ogg`/`oga`, even though `.opus` is Opus-in-Ogg and the bytes are identical. Confirmed by varying only the filename with the `Content-Type` held constant. Ogg-family audio is now presented to the provider under an accepted extension — via a symlink for unsplit files, so the user's own file is never renamed or copied

## [2.0.5] - 2026-07-30

### Added
- Plugin marketplace support for Claude Code and Codex (#63): the repository now carries `.claude-plugin/` (plugin + marketplace manifests) and `.codex-plugin/` + `.agents/plugins/` manifests, so the agent skill installs natively via `/plugin marketplace add lfnovo/content-core` (Claude Code) or via the Codex marketplace catalog

### Changed
- Agent skill moved from the repository root (`SKILL.md`) to `skills/content-core/SKILL.md` and refreshed (#63): Reddit capability documented, YouTube `live`/`shorts` URL forms, portable frontmatter, `--version`, updated model examples. The old raw-file URL no longer resolves — the README documents the new path and the marketplace install
- Minimum `esperanto` version raised to 2.26.0 (#70), which fixes every non-Whisper OpenAI and Azure transcription model: `verbose_json` was requested for anything that didn't match a narrow `gpt-4o-*-transcribe` name shape, so `gpt-transcribe` and friends failed before transcription started

### Fixed
- `.opus` files (the common export format for WhatsApp voice messages) raised `UnsupportedTypeException` instead of being transcribed (#69) — the extension was missing from the MIME mapping, and the Ogg container had no magic-byte signature at all. Ogg files are now detected by content as well as extension, with Opus/Vorbis/FLAC routed to audio and Theora to video
- Audio longer than 10 minutes failed for any non-MP3 source, including the already-supported `.flac` and `.ogg` (#69): segments were stream-copied but named `.mp3`, so ffmpeg refused to mux them. Segments now keep the source container

## [2.0.4] - 2026-07-12

### Added
- `check_file_support(file_path, config)` public API for cheap pre-flight validation of whether a file can be extracted, without running extraction; returns a `FileSupport` verdict

### Fixed
- YouTube `youtube.com/live/<id>` and `youtube.com/shorts/<id>` URLs were not recognized, causing title and transcript extraction to fail

## [2.0.3] - 2026-04-13

### Added
- `--version` flag to CLI (`content-core --version`)

## [2.0.2] - 2026-04-13

### Fixed
- LLM errors silently swallowed during summarization — errors now propagate with clear messages
- Thinking models (e.g., Ollama Qwen 3.5) return empty content — now uses `cleaned_content` from Esperanto 2.20.1
- Default LLM temperature changed from 0 to 0.5 and max_tokens from 600 to 4096 for compatibility with thinking models
- LLM timeout increased to 120s for local model providers

### Changed
- Bumped esperanto dependency to >=2.20.1 (thinking model support, trailing slash fix)

## [2.0.1] - 2026-04-13

### Fixed
- Summarize command fails via `uvx`/`pip install` — Jinja template was not packaged in the wheel

## [2.0.0] - 2026-04-11

### Added
- Docling enrichment flags: `docling_ocr`, `docling_formulas`, `docling_vision` for controlling OCR, formula extraction, and image/chart processing
- `ContentCoreConfig` based on pydantic-settings with `CCORE_` environment variable prefix for configuration (note: `FIRECRAWL_API_URL` and `CRAWL4AI_API_URL` use their standard names without the `CCORE_` prefix)
- Unified CLI command `content-core` with subcommands: `extract`, `summarize`, `mcp`
- `summarize_content` MCP tool for text summarization directly in Claude Desktop
- New configuration fields: `CCORE_LLM_PROVIDER`, `CCORE_LLM_MODEL`, `CCORE_STT_PROVIDER`, `CCORE_STT_MODEL`, `CCORE_STT_TIMEOUT`, `CCORE_YOUTUBE_LANGUAGES`
- Crawl4AI Docker mode (#23) — set `CRAWL4AI_API_URL` to use a remote Crawl4AI server instead of local Playwright
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
- MCP server invoked via `content-core mcp` instead of `content-core-mcp` (the `content-core-mcp` entry point is kept for backward compatibility)
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
