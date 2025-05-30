# Content Core Processors

**Note:** As of vNEXT, the default extraction engine is now `'auto'`. This means Content Core will automatically select the best extraction method based on your environment and available API keys, with a smart fallback order for both URLs and files. For files/documents, `'auto'` now tries Docling first, then falls back to simple extraction. See details below.

This document provides an overview of the content processors available in Content Core. These processors are responsible for extracting and handling content from various sources and file types.

## Overview

Content Core uses a modular approach to process content from different sources. Each processor is designed to handle specific types of input, such as web URLs, local files, or direct text input. Below, you'll find detailed information about each processor, including supported file types, returned data formats, and their purpose.

## Processors

### 1. **Text Processor**
- **Purpose**: Handles direct text input provided by the user.
- **Supported Input**: Raw text strings.
- **Returned Data**: The input text as-is, wrapped in a structured format compatible with Content Core's output schema.
- **Location**: `src/content_core/processors/text.py`

### 2. **Web (URL) Processor**
- **Purpose**: Extracts content from web URLs, focusing on meaningful text while ignoring boilerplate (ads, navigation, etc.).
- **Supported Input**: URLs (web pages).
- **Returned Data**: Extracted text content from the web page, often in a cleaned format.
- **Location**: `src/content_core/processors/url.py`
- **Default URL Engine (`auto`) Logic**:
    - If `FIRECRAWL_API_KEY` is set, uses Firecrawl for extraction.
    - Else it tries Jina until it fails because of rate limits (unless `JINA_API_KEY` is set).
    - Else, falls back to BeautifulSoup-based extraction.
    - You can explicitly specify a URL engine (`'firecrawl'`, `'jina'`, `'simple'`), but `'auto'` is now the default and recommended for most users.

### 3. **File Processor**
- **Purpose**: Processes local files of various types, extracting content based on file format.
- **Supported Input**: Local files including:
  - Text-based formats: `.txt`, `.md` (Markdown), `.html`, etc.
  - Document formats: `.pdf`, `.docx`, etc.
  - Media files: `.mp4`, `.mp3` (audio/video, via transcription).
- **Returned Data**: Extracted text content or transcriptions (for media files), structured according to Content Core's schema.
- **Location**: `src/content_core/processors/file.py`

### 4. **Media Transcription Processor**
- **Purpose**: Specifically handles transcription of audio and video files using external services or libraries.
- **Supported Input**: Audio and video files (e.g., `.mp3`, `.mp4`).
- **Returned Data**: Transcribed text from the media content.
- **Location**: `src/content_core/processors/transcription.py`

### 5. **Docling Processor**
- **Purpose**: Use Docling library for rich document parsing (PDF, DOCX, XLSX, PPTX, Markdown, AsciiDoc, HTML, CSV, images).
- **Supported Input**: PDF, DOCX, XLSX, PPTX, Markdown, AsciiDoc, HTML, CSV, Images (PNG, JPEG, TIFF, BMP).
- **Returned Data**: Content converted to configured format (markdown, html, json).
- **Location**: `src/content_core/processors/docling.py`
- **Default Document Engine (`auto`) Logic for Files/Documents**:
    - Tries the `'docling'` extraction method first (robust document parsing for supported types).
    - If `'docling'` fails or is not supported, automatically falls back to simple extraction (fast, lightweight for supported types).
    - You can explicitly specify `'docling'` or `'simple'` as the document engine, but `'auto'` is now the default and recommended for most users.
- **Configuration**: Activate the Docling engine in `cc_config.yaml` or custom config:
  ```yaml
  extraction:
    document_engine: docling  # 'auto' (default), 'simple', or 'docling'
    url_engine: auto          # 'auto' (default), 'simple', 'firecrawl', or 'jina'
    docling:
      output_format: markdown  # markdown | html | json
  ```
- **Programmatic Toggle**: Use helper functions in Python:
  ```python
  from content_core.config import set_document_engine, set_url_engine, set_docling_output_format

  # switch document engine to Docling
  set_document_engine("docling")
  
  # switch URL engine to Firecrawl
  set_url_engine("firecrawl")

  # choose output format
  set_docling_output_format("html")
  ```

## How Processors Work

Content Core automatically selects the appropriate processor based on the input type:
- If a URL is provided, the Web (URL) Processor is used.
- If a file path is provided, the File Processor determines the file type and delegates to specialized handlers (like the Media Transcription Processor for audio/video).
- If raw text is provided, the Text Processor handles it directly.

Each processor returns data in a consistent format, allowing seamless integration with other components of Content Core for further processing (like cleaning or summarization).

## Custom Processors

Developers can extend Content Core by creating custom processors for unsupported file types or specialized extraction needs. To do so, create a new processor module in `src/content_core/processors/` and ensure it adheres to the expected interface for integration with the content extraction pipeline.

## Contributing

If you have suggestions for improving existing processors or adding support for new file types, please contribute to the project by submitting a pull request or opening an issue on the GitHub repository.
