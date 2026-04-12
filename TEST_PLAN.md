# Content Core v2.0 — Test Plan

Status: 219 passed (unit+integration), 9 e2e (5 passed, 2 skipped, 2 failed pre-existing)

---

## Unit Tests (mocked, no I/O, no network)

`uv run pytest tests/unit -v`

### Configuration (`test_config_v2.py` — 34 tests)

- [x] Default values for all fields (document_engine, url_engine, audio_*, llm_*, stt_*, youtube_languages, pymupdf_*, docling_output_format)
- [x] Constructor override (url_engine, audio_concurrency, llm_model)
- [x] Environment variable override (CCORE_URL_ENGINE, CCORE_AUDIO_CONCURRENCY, CCORE_LLM_MODEL, CCORE_PYMUPDF_ENABLE_FORMULA_OCR)
- [x] List field from env (CCORE_YOUTUBE_LANGUAGES as JSON)
- [x] Validation: audio_concurrency boundaries (0 rejected, 11 rejected, 1 accepted, 10 accepted)
- [x] Priority: constructor beats env var
- [x] Singleton: get_default_config() returns same instance, reset clears it

### Routing / Orchestrator (`test_routing.py` — 14 tests)

- [x] Text input (content set) → calls `process_text`
- [x] YouTube URL (youtube.com) → calls `extract_youtube`
- [x] YouTube URL (youtu.be) → calls `extract_youtube`
- [x] Regular URL with article MIME → calls `extract_from_url`
- [x] Regular URL with PDF MIME → downloads file, calls `extract_pdf_file`
- [x] File with PDF MIME → calls `extract_pdf_file`
- [x] File with DOCX MIME → calls `extract_office`
- [x] File with video/* MIME → calls `extract_video`
- [x] File with audio/* MIME → calls `transcribe_audio`
- [x] File with text/plain MIME → calls `extract_text_file`
- [x] No source provided → raises InvalidInputError
- [x] Unknown MIME type → raises UnsupportedTypeException
- [x] Dict input converted to ExtractionInput
- [x] Config passed through to processor

### URL Engine Selection (`test_url_engine_select.py` — 5 tests)

- [x] auto + FIRECRAWL_API_KEY set → uses firecrawl
- [x] auto + no key → uses jina (with fallback chain)
- [x] engine="firecrawl" → uses firecrawl directly
- [x] engine="simple" → uses bs4 directly
- [x] engine="jina" → uses jina directly

### Text Processing (`test_text_processing.py` — 10 tests)

- [x] process_text: plain text returned unchanged
- [x] process_text: HTML content (2+ tags) converted to markdown
- [x] process_text: minimal HTML (1 tag) below threshold, unchanged
- [x] process_text: empty string returns empty ExtractionOutput
- [x] detect_html: headings + paragraphs → True
- [x] detect_html: plain text → False
- [x] detect_html: single tag below threshold
- [x] detect_html: multiple structural tags detected
- [x] extract_text_file: mocked file read returns content
- [x] extract_text_file: non-existent file raises FileNotFoundError

### YouTube Parsing (`test_youtube_parsing.py` — 9 tests)

- [x] _extract_youtube_id: standard URL (watch?v=ID)
- [x] _extract_youtube_id: short URL (youtu.be/ID)
- [x] _extract_youtube_id: embed URL (/embed/ID)
- [x] _extract_youtube_id: URL with extra params (watch?v=ID&t=120)
- [x] _extract_youtube_id: non-YouTube URL → None
- [x] extract_youtube: successful with mocked transcript + title
- [x] extract_youtube: transcript failure, pytubefix fallback succeeds
- [x] extract_youtube: both failures → empty content
- [x] extract_youtube: uses config.youtube_languages

### PDF Extraction (`test_pdf_extraction.py` — 11 tests)

- [x] clean_pdf_text: ligature "fi" replaced
- [x] clean_pdf_text: ligature "fl" replaced
- [x] clean_pdf_text: excessive whitespace collapsed
- [x] clean_pdf_text: hyphenation at line break merged
- [x] clean_pdf_text: empty string returns as-is
- [x] clean_pdf_text: None returns None
- [x] clean_pdf_text: multiple newlines collapsed
- [x] extract_pdf_file: successful extraction with mocked fitz
- [x] extract_pdf_file: EPUB identified type
- [x] extract_pdf_file: reads OCR settings from ContentCoreConfig
- [x] extract_pdf_file: non-existent file raises FileNotFoundError

### PDF OCR (`test_pymupdf_ocr.py` — 16 tests)

- [x] Formula placeholder counting (none, single, multiple, empty, None)
- [x] Table to markdown conversion (simple, empty cells, empty table, only empty cells)
- [x] OCR extraction (success, failure, empty result)
- [x] PDF integration: without OCR, OCR disabled by threshold, OCR fallback
- [x] Edge cases: malformed table

### Office Extraction (`test_office_extraction.py` — 8 tests)

- [x] extract_office: DOCX MIME → calls docx extractor
- [x] extract_office: PPTX MIME → calls pptx extractor
- [x] extract_office: XLSX MIME → calls xlsx extractor
- [x] extract_office: unknown MIME → raises ValueError
- [x] DOCX returns ExtractionOutput with content
- [x] PPTX returns slide content
- [x] XLSX returns table content
- [x] None content returns empty string

### Docling Extraction (`test_docling_extraction.py` — 6 tests)

- [x] extract_docling: markdown output format
- [x] extract_docling: HTML output format
- [x] extract_docling: JSON output format
- [x] extract_docling: default format is markdown
- [x] extract_docling: returns ExtractionOutput (not mutated state)
- [x] extract_docling: empty source raises ValueError

### Media Pipeline (`test_media_pipeline.py` — 9 tests)

- [x] transcribe_audio: default STT model from config
- [x] transcribe_audio: custom audio_provider + audio_model
- [x] transcribe_audio: uses stt_* config when no custom model
- [x] extract_video: successful extraction (mocked ffprobe + transcribe)
- [x] extract_video: no audio streams → error
- [x] extract_video: file not found raises
- [x] select_best_audio_stream: picks highest quality
- [x] select_best_audio_stream: empty list → None
- [x] get_audio_streams: parses mocked ffprobe JSON

### Audio Concurrency (`test_audio_concurrency.py` — 13 tests)

- [x] Default concurrency (3)
- [x] Environment variable override
- [x] Validation: 0, negative, too high rejected
- [x] Boundary: 1 and 10 accepted
- [x] Semaphore limits concurrency
- [x] Results maintain order
- [x] Single segment audio
- [x] Concurrency of 1 behaves serially
- [x] Empty audio file list
- [x] Single failure doesn't stop others

### Retry Decorators (`test_retry.py` — 22 tests)

- [x] Default config values
- [x] get_retry_config returns defaults for all 6 operation types
- [x] Unknown operation type fallback
- [x] Decorators: success first try, success after retry, exhausts retries
- [x] Network errors: connection error, timeout retried
- [x] All decorator types: youtube, url_api, url_network, audio, llm, download
- [x] Sync decorator support
- [x] Retryable vs non-retryable exception classification
- [x] NoTranscriptFound not retried

### File Detection (`test_file_detector*.py` — 18 tests)

- [x] PDF detection (correct, wrong extension, performance)
- [x] JSON detection (pretty-printed, reject JavaScript)
- [x] YAML/Markdown with front matter
- [x] MP4/M4A detection (ftyp variants)
- [x] JPEG detection (EXIF, Adobe markers)
- [x] Unicode handling with invalid bytes
- [x] DOCX via ZIP inspection
- [x] CSV detection
- [x] Error handling (non-existent, directory)
- [x] Performance: large files, multiple formats

### MCP Server (`test_mcp_v2.py` — 8 tests)

- [x] extract_content: URL extraction (mocked)
- [x] extract_content: file extraction (mocked)
- [x] extract_content: no params → error
- [x] extract_content: both params → error
- [x] extract_content: engine param forwarded to config
- [x] extract_content: extraction error handled
- [x] summarize_content: successful summarization (mocked)
- [x] summarize_content: error handled

### Data Models (`test_models_v2.py` — 9 tests)

- [x] ExtractionInput: no fields, url, file_path, content
- [x] ExtractionOutput: defaults, all fields, metadata isolation
- [x] Processor Protocol: conforming class passes, non-conforming fails

---

## Integration Tests (local files, no network)

`uv run pytest tests/integration -v`

### CLI (`test_cli_v2.py` — 10 tests)

- [x] --help shows extract/summarize/mcp
- [x] extract "Hello world" → outputs text
- [x] extract --format json → outputs valid JSON
- [x] extract --help shows --format and --engine
- [x] summarize --help shows --context
- [x] extract with no args → error
- [x] extract --engine simple "text" → accepted
- [x] extract with local fixture file → extracts content
- [x] summarize with stdin input → processes
- [x] --debug flag accepted

### File Extraction (`test_extraction.py` — 12 tests)

- [x] Text content extraction
- [x] HTML to markdown conversion (headings, lists, links)
- [x] Plain text unchanged (below threshold)
- [x] HTML detection threshold (requires 2+ structural tags)
- [x] Markdown file extraction
- [x] EPUB file extraction
- [x] PDF file extraction
- [x] PPTX file extraction
- [x] DOCX file extraction
- [x] XLSX file extraction

---

## E2E Tests (network + API keys, pre-release)

`uv run pytest tests/e2e -v -m e2e`

### URL Engines (`test_url_engines.py` — 5 tests)

- [x] BS4 extraction from real URL
- [ ] Firecrawl extraction (requires FIRECRAWL_API_KEY) — passes when key available
- [x] Jina extraction from real URL
- [ ] Crawl4AI extraction (requires playwright) — skipped if not installed
- [ ] Auto mode fallback (Jina fail → Crawl4AI) — skipped if crawl4ai not installed

### YouTube (`test_youtube.py` — 1 test)

- [x] Real YouTube transcript extraction

### Remote Files (`test_remote.py` — 1 test)

- [x] PDF download from arxiv.org

### Media Transcription (`test_media.py` — 2 tests)

- [ ] MP3 transcription via STT API — fails (pre-existing: diarization model needs chunking_strategy)
- [ ] MP4 transcription via STT API — fails (same issue)

---

## Known Issues

1. **MP3/MP4 e2e tests fail** — OpenAI API requires `chunking_strategy` for the `gpt-4o-transcribe-diarize` model. Fix: update default `stt_model` in config or update Esperanto library.
2. **Crawl4AI e2e tests skip** — Crawl4AI optional dependency not installed in dev environment.
