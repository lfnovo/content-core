# Changelog

All notable changes to Content Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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