# Configuration Guide

Content Core uses environment variables for all configuration. No YAML files are needed.

## Quick Reference

### Essential Environment Variables

```bash
# API Keys
export OPENAI_API_KEY=your-key          # Required for LLM operations
export FIRECRAWL_API_KEY=your-key       # Optional, for Firecrawl URL extraction
export JINA_API_KEY=your-key            # Optional, for higher Jina rate limits

# Engine Selection
export CCORE_DOCUMENT_ENGINE=auto       # auto, simple, docling, docling-vlm, marker
export CCORE_URL_ENGINE=auto            # auto, simple, firecrawl, jina, crawl4ai

# Audio Processing
export CCORE_AUDIO_CONCURRENCY=3        # 1-10, parallel transcriptions
```

## Configuration Priority

For each setting, the resolution order is:

1. **Programmatic override** (set via `set_*()` functions) - highest priority
2. **Environment variable**
3. **Default value** - lowest priority

## Engine Selection

### Document Engine

Controls how documents (PDF, DOCX, etc.) are extracted.

| Value | Description |
|-------|-------------|
| `auto` | Automatically select best available (default) |
| `simple` | Use PyMuPDF if available |
| `docling` | Use Docling (MIT license) |
| `docling-vlm` | Use VLM-powered Docling |
| `marker` | Use Marker (GPL-3.0) |

```bash
export CCORE_DOCUMENT_ENGINE=docling
```

### URL Engine

Controls how web URLs are extracted.

| Value | Description |
|-------|-------------|
| `auto` | Automatic selection with fallback (default) |
| `simple` | BeautifulSoup only |
| `firecrawl` | Firecrawl API (requires API key) |
| `jina` | Jina API |
| `crawl4ai` | Local browser extraction |

```bash
export CCORE_URL_ENGINE=auto
```

### Per MIME Type or Category

Fine-grained engine selection using ENV variables:

```bash
# Per MIME type
export CCORE_ENGINE_APPLICATION_PDF=docling-vlm,docling,pymupdf
export CCORE_ENGINE_APPLICATION_EPUB=docling
export CCORE_ENGINE_TEXT_HTML=jina,firecrawl

# Per category
export CCORE_ENGINE_DOCUMENTS=docling
export CCORE_ENGINE_URLS=jina,firecrawl
export CCORE_ENGINE_AUDIO=whisper
export CCORE_ENGINE_VIDEO=video

# Wildcard MIME types
export CCORE_ENGINE_IMAGE=docling
export CCORE_ENGINE_AUDIO=whisper
```

Engine chains are comma-separated. The first available engine is used; if it fails, the next one is tried.

## Docling Configuration

```bash
# Output format
export CCORE_DOCLING_OUTPUT_FORMAT=markdown  # markdown, html, json

# OCR settings
export CCORE_DOCLING_DO_OCR=true
export CCORE_DOCLING_OCR_ENGINE=easyocr      # easyocr, tesseract, rapidocr, ocrmac
export CCORE_DOCLING_FORCE_FULL_PAGE_OCR=false

# Table settings
export CCORE_DOCLING_TABLE_MODE=accurate     # accurate, fast
export CCORE_DOCLING_DO_TABLE_STRUCTURE=true

# Enrichment
export CCORE_DOCLING_DO_CODE_ENRICHMENT=false
export CCORE_DOCLING_DO_FORMULA_ENRICHMENT=true

# Image/picture handling
export CCORE_DOCLING_GENERATE_PAGE_IMAGES=false
export CCORE_DOCLING_GENERATE_PICTURE_IMAGES=false
export CCORE_DOCLING_IMAGES_SCALE=2.0
export CCORE_DOCLING_DO_PICTURE_CLASSIFICATION=false
export CCORE_DOCLING_DO_PICTURE_DESCRIPTION=false

# Picture description (when enabled)
export CCORE_DOCLING_PICTURE_MODEL=granite   # granite, smolvlm
export CCORE_DOCLING_PICTURE_PROMPT="Describe this image..."

# Timeout
export CCORE_DOCLING_DOCUMENT_TIMEOUT=300    # null for no limit
```

## VLM Configuration

For VLM-powered document extraction:

```bash
# Enable VLM
export CCORE_DOCUMENT_ENGINE=docling-vlm

# Inference mode
export CCORE_VLM_INFERENCE_MODE=local        # local, remote
export CCORE_VLM_BACKEND=auto                # auto, transformers, mlx
export CCORE_VLM_MODEL=granite-docling       # granite-docling, smol-docling

# Remote server (if using remote mode)
export CCORE_DOCLING_SERVE_URL=http://localhost:5001
export CCORE_DOCLING_SERVE_API_KEY=your-key
export CCORE_DOCLING_SERVE_TIMEOUT=120
```

See [Docling VLM Engine](engines/docling-vlm.md) for details.

## PyMuPDF Configuration

```bash
export CCORE_PYMUPDF_ENABLE_FORMULA_OCR=false
export CCORE_PYMUPDF_FORMULA_THRESHOLD=3
export CCORE_PYMUPDF_OCR_FALLBACK=true
```

## Marker Configuration

```bash
export CCORE_MARKER_USE_LLM=false
export CCORE_MARKER_FORCE_OCR=false
export CCORE_MARKER_PAGE_RANGE=null          # e.g., "0-10" for pages 0-10
export CCORE_MARKER_OUTPUT_FORMAT=markdown   # markdown, json, html
```

## Audio Configuration

```bash
# Concurrent transcriptions (1-10)
export CCORE_AUDIO_CONCURRENCY=3

# Timeout for speech-to-text
export ESPERANTO_STT_TIMEOUT=3600
```

## YouTube Configuration

```bash
# Preferred languages for transcripts (comma-separated)
export CCORE_YOUTUBE_LANGUAGES=en,es,pt
```

## Fallback Configuration

Control behavior when an engine fails:

```bash
export CCORE_FALLBACK_ENABLED=true
export CCORE_FALLBACK_MAX_ATTEMPTS=3
export CCORE_FALLBACK_ON_ERROR=warn          # next, warn, fail
```

- `next`: Try next engine silently
- `warn`: Log warning and try next engine
- `fail`: Raise error immediately

## Retry Configuration

Configure retry behavior for transient failures:

```bash
# YouTube
export CCORE_YOUTUBE_MAX_RETRIES=5
export CCORE_YOUTUBE_BASE_DELAY=2
export CCORE_YOUTUBE_MAX_DELAY=60

# URL APIs (Firecrawl, Jina, Crawl4AI)
export CCORE_URL_API_MAX_RETRIES=3
export CCORE_URL_API_BASE_DELAY=1
export CCORE_URL_API_MAX_DELAY=30

# Audio transcription
export CCORE_AUDIO_MAX_RETRIES=3
export CCORE_AUDIO_BASE_DELAY=2
export CCORE_AUDIO_MAX_DELAY=30

# LLM calls
export CCORE_LLM_MAX_RETRIES=3
export CCORE_LLM_BASE_DELAY=1
export CCORE_LLM_MAX_DELAY=30

# File downloads
export CCORE_DOWNLOAD_MAX_RETRIES=3
export CCORE_DOWNLOAD_BASE_DELAY=1
export CCORE_DOWNLOAD_MAX_DELAY=15
```

## Model Configuration

Configure AI models for LLM operations:

```bash
# Speech-to-text
export CCORE_SPEECH_TO_TEXT_PROVIDER=openai
export CCORE_SPEECH_TO_TEXT_MODEL=gpt-4o-transcribe-diarize
export CCORE_SPEECH_TO_TEXT_TIMEOUT=3600

# Default LLM
export CCORE_DEFAULT_MODEL_PROVIDER=openai
export CCORE_DEFAULT_MODEL_MODEL=gpt-4o-mini
export CCORE_DEFAULT_MODEL_TIMEOUT=300

# Cleanup model
export CCORE_CLEANUP_MODEL_PROVIDER=openai
export CCORE_CLEANUP_MODEL_MODEL=gpt-4o-mini
export CCORE_CLEANUP_MODEL_TIMEOUT=600

# Summary model
export CCORE_SUMMARY_MODEL_PROVIDER=openai
export CCORE_SUMMARY_MODEL_MODEL=gpt-4o-mini
export CCORE_SUMMARY_MODEL_TIMEOUT=300
```

## Firecrawl Configuration

```bash
# Custom API URL (for self-hosted Firecrawl)
export FIRECRAWL_API_BASE_URL=http://localhost:3002

# API key
export FIRECRAWL_API_KEY=your-key
```

## Proxy Configuration

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
```

**Note:** Firecrawl does not support client-side proxy.

## Extraction Timeout

```bash
export CCORE_EXTRACTION_TIMEOUT=300
```

## Custom Prompts

Override default prompts:

```bash
export PROMPT_PATH=/path/to/custom/prompts
```

Place custom prompt templates in this directory.

## Programmatic Configuration

Use setter functions for programmatic configuration:

```python
from content_core.config import (
    set_document_engine,
    set_url_engine,
    set_audio_concurrency,
    set_docling_output_format,
    set_firecrawl_api_url,
    set_vlm_inference_mode,
    set_vlm_backend,
    set_vlm_model,
    set_vlm_remote_url,
    reset_config,
)

# Engine selection
set_document_engine("docling")
set_url_engine("firecrawl")

# Docling settings
set_docling_output_format("html")

# Audio settings
set_audio_concurrency(5)

# Firecrawl self-hosted
set_firecrawl_api_url("http://localhost:3002")

# VLM settings
set_vlm_inference_mode("remote")
set_vlm_backend("transformers")
set_vlm_model("granite-docling")
set_vlm_remote_url("http://gpu-server:5001")

# Reset all programmatic overrides
reset_config()
```

## Per-Request Overrides

Override settings for specific requests using the new API:

```python
from content_core import extract_content

# Override engine for this request
result = await extract_content(
    file_path="document.pdf",
    engine="docling-vlm",  # Use specific engine
)

# Use engine chain
result = await extract_content(
    file_path="document.pdf",
    engine=["docling-vlm", "docling", "pymupdf"],  # Try in order
)
```

## Migration from YAML Configuration

If you were using YAML configuration files (`cc_config.yaml` or `models_config.yaml`), migrate to ENV variables:

**Before (YAML):**
```yaml
extraction:
  document_engine: docling
  docling:
    output_format: html
    options:
      do_ocr: true
      do_picture_description: true
```

**After (ENV):**
```bash
export CCORE_DOCUMENT_ENGINE=docling
export CCORE_DOCLING_OUTPUT_FORMAT=html
export CCORE_DOCLING_DO_OCR=true
export CCORE_DOCLING_DO_PICTURE_DESCRIPTION=true
```

**Note:** `CCORE_CONFIG_PATH` and `CCORE_MODEL_CONFIG_PATH` are deprecated and ignored.

## Complete ENV Reference

### Engine Selection
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_DOCUMENT_ENGINE` | auto, simple, docling, docling-vlm, marker | auto |
| `CCORE_URL_ENGINE` | auto, simple, firecrawl, jina, crawl4ai | auto |
| `CCORE_ENGINE_{MIME_TYPE}` | comma-separated engines | - |
| `CCORE_ENGINE_{CATEGORY}` | comma-separated engines | - |

### Docling Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_DOCLING_OUTPUT_FORMAT` | markdown, html, json | markdown |
| `CCORE_DOCLING_DO_OCR` | true, false | true |
| `CCORE_DOCLING_OCR_ENGINE` | easyocr, tesseract, etc. | easyocr |
| `CCORE_DOCLING_FORCE_FULL_PAGE_OCR` | true, false | false |
| `CCORE_DOCLING_TABLE_MODE` | accurate, fast | accurate |
| `CCORE_DOCLING_DO_TABLE_STRUCTURE` | true, false | true |
| `CCORE_DOCLING_DO_CODE_ENRICHMENT` | true, false | false |
| `CCORE_DOCLING_DO_FORMULA_ENRICHMENT` | true, false | true |
| `CCORE_DOCLING_GENERATE_PAGE_IMAGES` | true, false | false |
| `CCORE_DOCLING_GENERATE_PICTURE_IMAGES` | true, false | false |
| `CCORE_DOCLING_IMAGES_SCALE` | float | 2.0 |
| `CCORE_DOCLING_DO_PICTURE_CLASSIFICATION` | true, false | false |
| `CCORE_DOCLING_DO_PICTURE_DESCRIPTION` | true, false | false |
| `CCORE_DOCLING_PICTURE_MODEL` | granite, smolvlm | granite |
| `CCORE_DOCLING_DOCUMENT_TIMEOUT` | integer or null | null |

### VLM Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_VLM_INFERENCE_MODE` | local, remote | local |
| `CCORE_VLM_BACKEND` | auto, transformers, mlx | auto |
| `CCORE_VLM_MODEL` | granite-docling, smol-docling | granite-docling |
| `CCORE_DOCLING_SERVE_URL` | URL | http://localhost:5001 |
| `CCORE_DOCLING_SERVE_API_KEY` | string | null |
| `CCORE_DOCLING_SERVE_TIMEOUT` | integer (1-3600) | 120 |

### Marker Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_MARKER_USE_LLM` | true, false | false |
| `CCORE_MARKER_FORCE_OCR` | true, false | false |
| `CCORE_MARKER_PAGE_RANGE` | string or null | null |
| `CCORE_MARKER_OUTPUT_FORMAT` | markdown, json, html | markdown |

### PyMuPDF Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_PYMUPDF_ENABLE_FORMULA_OCR` | true, false | false |
| `CCORE_PYMUPDF_FORMULA_THRESHOLD` | integer | 3 |
| `CCORE_PYMUPDF_OCR_FALLBACK` | true, false | true |

### Fallback Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_FALLBACK_ENABLED` | true, false | true |
| `CCORE_FALLBACK_MAX_ATTEMPTS` | integer (1-10) | 3 |
| `CCORE_FALLBACK_ON_ERROR` | next, warn, fail | warn |

### Audio Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_AUDIO_CONCURRENCY` | integer (1-10) | 3 |

### YouTube Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_YOUTUBE_LANGUAGES` | comma-separated codes | en,es,pt |

### Retry Options
| Variable | Values | Default |
|----------|--------|---------|
| `CCORE_{TYPE}_MAX_RETRIES` | integer (1-20) | varies |
| `CCORE_{TYPE}_BASE_DELAY` | float (0.1-60) | varies |
| `CCORE_{TYPE}_MAX_DELAY` | float (1-300) | varies |

Where `{TYPE}` is one of: `YOUTUBE`, `URL_API`, `URL_NETWORK`, `AUDIO`, `LLM`, `DOWNLOAD`
