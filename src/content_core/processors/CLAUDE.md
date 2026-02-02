# Processors Module

Format-specific content extraction handlers. Each processor extracts content from a specific file type or source.

## Architecture (v2.0)

Processors now follow a registry-based pattern:

1. **Base classes** (`base.py`): `Processor`, `ProcessorCapabilities`, `ProcessorResult`, `Source`
2. **Registry** (`registry.py`): `ProcessorRegistry` singleton, `@processor()` decorator
3. **Auto-discovery** (`__init__.py`): Imports all processors to trigger registration

**Creating a new processor:**
```python
from content_core.processors.base import Processor, ProcessorResult, Source
from content_core.processors.registry import processor

@processor(
    name="my-processor",
    mime_types=["application/pdf", "image/*"],
    extensions=[".pdf", ".png"],
    priority=60,  # Higher = preferred (0-100)
    requires=["my-dependency"],
    category="documents",
)
class MyProcessor(Processor):
    @classmethod
    def is_available(cls) -> bool:
        return MY_DEPENDENCY_AVAILABLE

    async def extract(self, source: Source, options=None) -> ProcessorResult:
        # source.file_path, source.url, or source.content
        content = await my_extraction_logic(source.file_path)
        return ProcessorResult(
            content=content,
            mime_type=source.mime_type,
            metadata={"extraction_engine": "my-processor"},
        )
```

## Files

- **`__init__.py`**: Auto-discovery, exports `ProcessorRegistry`, `Processor`, `Source`, `ProcessorResult`
- **`base.py`**: Base classes for processor system
- **`registry.py`**: `ProcessorRegistry` singleton and `@processor()` decorator
- **`pdf.py`**: PDF/EPUB via PyMuPDF (`PyMuPDFProcessor`, priority 50)
- **`pdf_llm.py`**: PDF via pymupdf4llm (`PyMuPDF4LLMProcessor`, priority 55)
- **`url.py`**: URL extraction (`JinaProcessor` 60, `FirecrawlProcessor` 65, `Crawl4AIProcessor` 55, `BS4Processor` 40)
- **`audio.py`**: Audio transcription (`WhisperProcessor`, priority 60)
- **`video.py`**: Video-to-audio (`VideoProcessor`, priority 50)
- **`youtube.py`**: YouTube transcripts (`YouTubeProcessor`, priority 60)
- **`office.py`**: Office docs (`OfficeProcessor`, priority 50)
- **`text.py`**: Plain text (`TextProcessor`, priority 50)
- **`docling.py`**: Docling integration (`DoclingProcessor`, priority 60)
- **`docling_vlm.py`**: VLM-powered extraction (`DoclingVLMProcessor`, priority 70)
- **`marker.py`**: Marker PDF extraction (`MarkerProcessor`, priority 65, GPL-3.0)

## Picture Description

The `docling.py` processor supports VLM-based image captioning when `do_picture_description=True`.

**Configuration (env vars or YAML):**
- `CCORE_DOCLING_DO_PICTURE_DESCRIPTION=true` - Enable picture description
- `CCORE_DOCLING_PICTURE_MODEL=granite` - Model: `smolvlm` (256M, faster) or `granite` (2B, better)
- `CCORE_DOCLING_PICTURE_PROMPT="..."` - Custom prompt for image description

**Important notes:**
- Forces CPU device due to MPS (Apple Silicon) compatibility issues
- Descriptions stored in `pic.meta.description.text`, not exported to markdown
- Use `docling` engine (not `docling-vlm`) for reliable picture descriptions
- See: https://github.com/docling-project/docling/discussions/2434

## Patterns

**New v2.0 Pattern (Processor classes):**
- Processors are classes decorated with `@processor()` that implement `Processor.extract(source, options)`
- Each processor declares capabilities: MIME types, extensions, priority, required dependencies
- Registry auto-selects highest priority available processor for a given MIME type
- `is_available()` class method checks if optional dependencies are installed

**Legacy Pattern (still supported):**
- Extract functions take `ProcessSourceState` and return `Dict[str, Any]` with content/metadata updates
- Used by LangGraph workflow in `content/extraction/graph.py`
- Processor classes wrap legacy functions for backward compatibility

**Common patterns:**
- **Async execution**: CPU-bound work runs in thread pool via `asyncio.get_event_loop().run_in_executor()`
- **Retry decorators**: Network operations wrapped with retry decorators from `common.retry`
- **Type constants**: Each processor exports `SUPPORTED_*_TYPES` lists for legacy routing

## Integration

**New API (v2.0):**
- Called by: `content/extraction/router.py` via `ProcessorRegistry`
- Access: `ProcessorRegistry.instance().find_for_mime_type("application/pdf")`

**Legacy API:**
- Called by: `content/extraction/graph.py` via LangGraph nodes

**Common:**
- Imports from: `content_core.common`, `content_core.config`, `content_core.logging`, `content_core.models`
- `audio.py` uses `ModelFactory.get_model("speech_to_text")` for STT

## Gotchas

- `docling.py` is conditionally imported - check `DOCLING_AVAILABLE` before using
- `docling_vlm.py` is conditionally imported - check `DOCLING_VLM_LOCAL_AVAILABLE` for local, `HTTPX_AVAILABLE` for remote
- `url.py` fallback chain: Firecrawl (if API key) -> Jina -> Crawl4AI -> BeautifulSoup
- `audio.py` segments files >10 min and processes in parallel with configurable concurrency
- `pdf.py` OCR is disabled by default - enable via config `extraction.pymupdf.enable_formula_ocr`
- Proxy is configured via standard HTTP_PROXY/HTTPS_PROXY environment variables (use `trust_env=True` with aiohttp)

## When Adding Code

**New v2.0 Pattern (preferred):**
1. Create a class that extends `Processor`
2. Decorate with `@processor(name=..., mime_types=..., priority=..., ...)`
3. Implement `is_available()` if processor has optional dependencies
4. Implement `async extract(self, source: Source, options: dict) -> ProcessorResult`
5. Processor auto-registers when module is imported (via `processors/__init__.py`)

**Legacy Pattern (if needed for LangGraph integration):**
- Create extract function that accepts `ProcessSourceState`, returns dict with state updates
- Add MIME types to `SUPPORTED_*_TYPES` constant
- Register as node in `content/extraction/graph.py`

**Common:**
- Network operations should use retry decorators for resilience
- For aiohttp sessions, use `trust_env=True` for HTTP_PROXY/HTTPS_PROXY
- Handle errors gracefully, return empty content on failure rather than raising
