# Engine Config Module

Configuration management for engine selection and fallback behavior in content extraction.

## Files

- **`__init__.py`**: Exports `EngineResolver`, `ExtractionConfig`, `FallbackConfig`, ENV parsing functions
- **`schema.py`**: Pydantic models for configuration
  - `FallbackConfig`: Controls fallback behavior (enabled, max_attempts, on_error, fatal_errors)
  - `ExtractionConfig`: Full extraction config (timeout, engines, fallback, engine_options, legacy config)
- **`env.py`**: ENV variable parsing for engine chains
  - `CCORE_ENGINE_{MIME_TYPE}` (e.g., `CCORE_ENGINE_APPLICATION_PDF=docling-vlm,docling`)
  - `CCORE_ENGINE_{CATEGORY}` (e.g., `CCORE_ENGINE_DOCUMENTS=docling`)
  - `CCORE_FALLBACK_*` (ENABLED, MAX_ATTEMPTS, ON_ERROR)
- **`resolver.py`**: `EngineResolver` class that resolves engine chains

## Engine Resolution Order

1. **Explicit param**: `extract_content(..., engine="docling")`
2. **ENV specific MIME**: `CCORE_ENGINE_APPLICATION_PDF`
3. **YAML specific MIME**: `engines["application/pdf"]`
4. **ENV wildcard MIME**: `CCORE_ENGINE_IMAGE`
5. **YAML wildcard MIME**: `engines["image/*"]`
6. **ENV category**: `CCORE_ENGINE_DOCUMENTS`
7. **YAML category**: `engines["documents"]`
8. **Legacy config**: `document_engine`/`url_engine`
9. **Auto-detect**: Highest priority processor from registry

## Usage

```python
from content_core.config import get_extraction_config
from content_core.engine_config import EngineResolver

config = get_extraction_config()
resolver = EngineResolver(config)

# Resolve engines for a MIME type
engines = resolver.resolve("application/pdf")
# Returns: ['docling-vlm', 'docling', 'pymupdf'] based on config

# With explicit override
engines = resolver.resolve("application/pdf", explicit="pymupdf")
# Returns: ['pymupdf']
```

## YAML Configuration

```yaml
extraction:
  timeout: 300

  engines:
    "application/pdf":
      - docling-vlm
      - docling
    "image/*": docling
    documents: docling
    urls: jina

  fallback:
    enabled: true
    max_attempts: 3
    on_error: warn  # next | warn | fail
    fatal_errors:
      - FileNotFoundError
      - PermissionError

  engine_options:
    docling:
      do_ocr: true
```

## ENV Variables

```bash
# Per MIME type
CCORE_ENGINE_APPLICATION_PDF=docling-vlm,docling,pymupdf
CCORE_ENGINE_IMAGE=docling

# Per category
CCORE_ENGINE_DOCUMENTS=docling
CCORE_ENGINE_URLS=jina,firecrawl

# Fallback config
CCORE_FALLBACK_ENABLED=true
CCORE_FALLBACK_MAX_ATTEMPTS=3
CCORE_FALLBACK_ON_ERROR=warn
```

## Integration

- **Called by**: `content/extraction/router.py` to resolve engines
- **Uses**: `ProcessorRegistry` for auto-detection
- **Imported from**: `content_core.config` (get_extraction_config)

## Gotchas

- ENV variables use underscores instead of slashes/plus (e.g., `APPLICATION_PDF` not `application/pdf`)
- Engine chains are comma-separated in ENV vars
- `on_error="fail"` raises immediately without trying other engines
- `fatal_errors` list uses exception class names as strings
- Legacy config (`document_engine`/`url_engine`) is step 8, before auto-detect
