# Configuration Guide

Content Core can be configured through environment variables, YAML files, or programmatically.

## Quick Reference

### Essential Environment Variables

```bash
# API Keys
export OPENAI_API_KEY=your-key          # Required for LLM operations
export FIRECRAWL_API_KEY=your-key       # Optional, for Firecrawl URL extraction
export JINA_API_KEY=your-key            # Optional, for higher Jina rate limits

# Engine Selection
export CCORE_DOCUMENT_ENGINE=auto       # auto, simple, docling, docling-vlm
export CCORE_URL_ENGINE=auto            # auto, simple, firecrawl, jina, crawl4ai

# Audio Processing
export CCORE_AUDIO_CONCURRENCY=3        # 1-10, parallel transcriptions
```

## Engine Selection

### Document Engine

Controls how documents (PDF, DOCX, etc.) are extracted.

| Value | Description |
|-------|-------------|
| `auto` | Automatically select best available (default) |
| `simple` | Use PyMuPDF if available |
| `docling` | Use Docling (MIT license) |
| `docling-vlm` | Use VLM-powered Docling |

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

## YAML Configuration

Create `cc_config.yaml` in your project root:

```yaml
extraction:
  document_engine: auto
  url_engine: auto

  firecrawl:
    api_url: null  # Custom URL for self-hosted

  docling:
    output_format: markdown  # markdown, html, json
    options:
      do_picture_description: false
      picture_description_model: granite

  pymupdf:
    enable_formula_ocr: false
    formula_threshold: 3
    ocr_fallback: true

  audio:
    concurrency: 3

# AI Model Configuration
speech_to_text:
  provider: openai
  model_name: whisper-1
  timeout: 3600

default_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0.5
    max_tokens: 2000

cleanup_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 8000
    timeout: 600

summary_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 2000
    timeout: 300
```

Point to your config file:

```bash
export CCORE_MODEL_CONFIG_PATH=/path/to/cc_config.yaml
```

## Programmatic Configuration

```python
from content_core.config import (
    set_document_engine,
    set_url_engine,
    set_docling_output_format,
    set_audio_concurrency,
    set_firecrawl_api_url,
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
```

## VLM Configuration

For VLM-powered document extraction:

```bash
# Enable VLM
export CCORE_DOCUMENT_ENGINE=docling-vlm

# Inference mode
export CCORE_VLM_INFERENCE_MODE=local  # local or remote
export CCORE_VLM_BACKEND=auto          # auto, transformers, mlx
export CCORE_VLM_MODEL=granite-docling # granite-docling, smol-docling

# Remote server (if using remote mode)
export CCORE_DOCLING_SERVE_URL=http://localhost:5001
export CCORE_DOCLING_SERVE_API_KEY=your-key
export CCORE_DOCLING_SERVE_TIMEOUT=120
```

See [Docling VLM Engine](engines/docling-vlm.md) for details.

## Audio Configuration

```bash
# Concurrent transcriptions (1-10)
export CCORE_AUDIO_CONCURRENCY=3

# Timeout for speech-to-text
export ESPERANTO_STT_TIMEOUT=3600
```

## Retry Configuration

Configure retry behavior for transient failures:

```bash
# YouTube
export CCORE_YOUTUBE_MAX_RETRIES=5
export CCORE_YOUTUBE_BASE_DELAY=2
export CCORE_YOUTUBE_MAX_DELAY=60

# URL APIs (Firecrawl, Jina)
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
```

## Proxy Configuration

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1
```

**Note:** Firecrawl does not support client-side proxy.

## Timeout Configuration

```bash
# LLM timeout
export ESPERANTO_LLM_TIMEOUT=300

# Speech-to-text timeout
export ESPERANTO_STT_TIMEOUT=3600
```

## Custom Prompts

Override default prompts:

```bash
export PROMPT_PATH=/path/to/custom/prompts
```

Place custom prompt templates in this directory.

## Per-Request Overrides

Override settings for specific requests:

```python
from content_core.common.state import ProcessSourceInput
from content_core.content.extraction import extract_content

result = await extract_content(ProcessSourceInput(
    file_path="document.pdf",
    document_engine="docling-vlm",
    output_format="html",
    vlm_inference_mode="remote",
    vlm_remote_url="http://gpu-server:5001",
))
```

## Configuration Priority

1. Per-request parameters (highest)
2. Environment variables
3. YAML configuration file
4. Default values (lowest)
