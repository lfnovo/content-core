# Content Core Processors

This document describes how Content Core extracts content from different source types. Processors are organized into three categories: URL, document, and media.

## Overview

Content Core automatically selects the appropriate processor based on input:

- **URL provided** -- routes to a URL processor (or YouTube processor for YouTube links)
- **File path provided** -- file type is detected, then routed to the matching document or media processor
- **Text provided** -- handled by the text processor

File type detection is done in pure Python using binary signatures and content analysis. No system library (like libmagic) is required.

## URL Processors

Located in `src/content_core/processors/url/`.

### Engine Selection

The `url_engine` setting controls which processor handles web URLs. When set to `auto` (the default), Content Core tries engines in this order:

1. **Firecrawl** -- if `FIRECRAWL_API_KEY` is set
2. **Jina** -- uses Jina Reader API (works without API key, but `JINA_API_KEY` avoids rate limits)
3. **Crawl4AI** -- if installed (`pip install content-core[crawl4ai]`)
4. **BeautifulSoup** -- always available as the final fallback

### BeautifulSoup (`simple`)

- File: `bs4.py`
- Fetches HTML via aiohttp and extracts meaningful text
- No external API keys required
- Suitable for simple pages; may struggle with JavaScript-heavy sites

### Jina (`jina`)

- File: `jina.py`
- Uses Jina Reader API for clean content extraction
- Works without an API key, but setting `JINA_API_KEY` avoids rate limits
- Good for articles and documentation pages

### Firecrawl (`firecrawl`)

- File: `firecrawl.py`
- Uses the Firecrawl API for high-quality web extraction
- Requires `FIRECRAWL_API_KEY`
- Supports self-hosted instances via `FIRECRAWL_API_URL`
- Configurable proxy (`CCORE_FIRECRAWL_PROXY`, default: `auto`) — retries with stealth proxies on anti-bot blocks
- Configurable wait time (`CCORE_FIRECRAWL_WAIT_FOR`, default: `3000`ms) — waits for dynamic content before extraction

### Reddit (automatic)

- File: `reddit.py`
- Automatically detects Reddit post URLs and extracts via the public `.json` endpoint
- Extracts post title, body, metadata (author, score, subreddit), and full comment tree with nested replies
- No API key or authentication needed for public posts
- Falls back to the configured URL engine if JSON extraction fails
- Supports `www.reddit.com`, `old.reddit.com`, and `new.reddit.com`

### Crawl4AI (`crawl4ai`)

- File: `crawl4ai.py`
- Two modes: local browser automation or Docker API
- **Local mode** (default): Requires `pip install content-core[crawl4ai]` and `python -m playwright install --with-deps`
- **Docker mode**: Set `CRAWL4AI_API_URL` (e.g., `http://localhost:11235`) to use a remote Crawl4AI container — no local Playwright needed
- No API keys needed; all processing happens locally or on your server
- Handles JavaScript-heavy sites well

## Document Processors

Located in `src/content_core/processors/document/`.

### Engine Selection

The `document_engine` setting controls document processing. When set to `auto` (the default):

1. **Docling** -- tried first if installed
2. **Simple** -- pdfplumber for PDF, fast-ebook for EPUB, native parsers for Office formats

### PDF (Simple Engine)

- File: `document/pdf.py`
- Uses pdfplumber for text and table extraction
- Features:
  - Automatic table detection and conversion to markdown
  - Text cleaning (ligatures, whitespace, hyphenation normalization)

### EPUB

- File: `document/epub.py`
- Uses fast-ebook (Rust-powered) for EPUB2/EPUB3 extraction
- Converts EPUB content to markdown

### DOCX

- File: `document/docx.py`
- Extracts text from Word documents using python-docx

### PPTX

- File: `document/pptx.py`
- Extracts text from PowerPoint slides

### XLSX

- File: `document/xlsx.py`
- Extracts data from Excel spreadsheets

### Docling (Optional)

- File: `document/docling.py`
- Supports two backends selected per request config:
  - Remote Docling Serve via `DOCLING_API_URL` / `docling_api_url`
  - Local Docling via `pip install content-core[docling]`
- Supports PDF, DOCX, PPTX, XLSX, Markdown, AsciiDoc, HTML, CSV, and images
- Remote Docling Serve currently returns markdown from the synchronous `POST /v1/convert/file` API
- Local Docling preserves configurable output format: markdown (default), HTML, or JSON
- Provides richer structural parsing than the simple engine
- Routing precedence is remote API first, then local Docling, then the existing simple fallback

## Media Processors

Located in `src/content_core/processors/media/`.

### Audio

- File: `media/audio.py`
- Transcribes audio files using speech-to-text (default: OpenAI Whisper)
- Supported formats: MP3, WAV, M4A, FLAC, OGG
- Uses ffmpeg/ffprobe for duration detection and segment splitting (stream copy, no re-encoding)
- Features:
  - Files longer than 10 minutes are automatically split into segments
  - Segments are transcribed in parallel with configurable concurrency (1-10, default 3)
  - Results are assembled in correct order regardless of completion time
  - Custom STT provider and model can be specified per call

### Video

- File: `media/video.py`
- Extracts audio from video files, then transcribes using the audio processor
- Supported formats: MP4, AVI, MOV, MKV
- Uses ffmpeg/ffprobe for audio stream selection and extraction

## YouTube Processor

- File: `processors/url/youtube.py`
- Extracts transcripts from YouTube videos
- Uses youtube-transcript-api (primary) with pytubefix as fallback
- Supports configurable language preferences via `CCORE_YOUTUBE_LANGUAGES`
- Automatic retry with backoff for rate limiting

## Text Processor

- File: `processors/text.py`
- Handles direct text input
- Automatically detects HTML content and converts it to markdown using markdownify
- Plain text passes through unchanged

## File Type Detection

- Located in `src/content_core/content/identification/file_detector.py`
- Pure Python implementation, no system dependencies
- Detection methods:
  - Binary signature matching for PDF, images, audio, video, and archives
  - ZIP structure inspection for Office formats (DOCX, XLSX, PPTX) and EPUB
  - Content analysis for text-based formats (HTML, XML, JSON, YAML, CSV, Markdown)
- Reads only the first 512 bytes for binary signatures and 1024 bytes for text content analysis
- Works regardless of file extension
