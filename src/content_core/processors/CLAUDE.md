# Processors Module

Format-specific content extraction handlers. Each processor extracts content from a specific file type or source.

## Files

- **`pdf.py`**: PDF/EPUB extraction using PyMuPDF (fitz). Handles table detection, OCR fallback for formulas, text cleaning. Exports `SUPPORTED_FITZ_TYPES`, `extract_pdf`
- **`url.py`**: URL content extraction with multiple engines (simple/jina/firecrawl/crawl4ai). Handles MIME type detection via HEAD request. Exports `url_provider`, `extract_url`
- **`audio.py`**: Audio transcription using Esperanto STT models. Handles segmentation for long files, parallel transcription with semaphore. Exports `extract_audio_data`
- **`video.py`**: Video-to-audio extraction using moviepy. Extracts audio track for transcription pipeline. Exports `extract_best_audio_from_video`
- **`youtube.py`**: YouTube transcript extraction using youtube-transcript-api. Handles multiple transcript formats, language fallbacks. Exports `extract_youtube_transcript`
- **`office.py`**: Office document extraction (docx, pptx, xlsx) using python-docx, python-pptx, openpyxl. Exports `SUPPORTED_OFFICE_TYPES`, `extract_office_content`
- **`text.py`**: Plain text file reading and HTML-to-markdown conversion. Detects HTML in text content and converts to markdown using `markdownify`. Exports `extract_txt`, `process_text_content`, `detect_html`
- **`docling.py`**: Optional Docling-based extraction for advanced document processing. Conditionally imported. Exports `DOCLING_AVAILABLE`, `DOCLING_SUPPORTED`, `extract_with_docling`
- **`docling_vlm.py`**: VLM-powered extraction using Docling's VlmPipeline or docling-serve. Supports local inference (transformers/MLX) and remote inference. Exports `DOCLING_VLM_LOCAL_AVAILABLE`, `DOCLING_VLM_MLX_AVAILABLE`, `HTTPX_AVAILABLE`, `extract_with_docling_vlm`, `extract_with_vlm_local`, `extract_with_vlm_remote`

## Patterns

- **Function signature**: All extract functions take `ProcessSourceState` and return `Dict[str, Any]` with content/metadata updates
- **Async execution**: CPU-bound work runs in thread pool via `asyncio.get_event_loop().run_in_executor()`
- **Retry decorators**: Network operations wrapped with retry decorators from `common.retry`
- **Engine selection**: URL and document engines selected via `config.get_url_engine()` / `config.get_document_engine()`
- **Type constants**: Each processor exports `SUPPORTED_*_TYPES` lists used by the routing graph

## Integration

- Called by: `content/extraction/graph.py` via LangGraph nodes
- Imports from: `content_core.common`, `content_core.config`, `content_core.logging`, `content_core.models`
- `audio.py` uses `ModelFactory.get_model("speech_to_text")` for STT

## Gotchas

- `docling.py` is conditionally imported - check `DOCLING_AVAILABLE` before using
- `docling_vlm.py` is conditionally imported - check `DOCLING_VLM_LOCAL_AVAILABLE` for local, `HTTPX_AVAILABLE` for remote
- `url.py` fallback chain: Firecrawl (if API key) -> Jina -> Crawl4AI -> BeautifulSoup
- `audio.py` segments files >10 min and processes in parallel with configurable concurrency
- `pdf.py` OCR is disabled by default - enable via config `extraction.pymupdf.enable_formula_ocr`
- All processors must handle the `proxy` field from state when making network requests

## When Adding Code

- New processors must: accept `ProcessSourceState`, return dict with state updates, handle errors gracefully
- Add new MIME types to the appropriate `SUPPORTED_*_TYPES` constant
- Network operations should use retry decorators and `get_proxy()` for proxy support
- Register new processors as nodes in `content/extraction/graph.py`
