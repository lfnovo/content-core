# Engine Config Module

Configuration management for engine selection and fallback behavior in content extraction.

**v2.0 Breaking Change:** YAML configuration is no longer supported. All configuration is done via ENV variables.

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

## Engine Resolution Order (v2.0 - ENV only)

1. **Explicit param**: `extract_content(..., engine="docling")`
2. **ENV specific MIME**: `CCORE_ENGINE_APPLICATION_PDF`
3. **ENV wildcard MIME**: `CCORE_ENGINE_IMAGE`
4. **ENV category**: `CCORE_ENGINE_DOCUMENTS`
5. **Legacy config**: `document_engine`/`url_engine` (via `CCORE_DOCUMENT_ENGINE`/`CCORE_URL_ENGINE`)
6. **Auto-detect**: Highest priority processor from registry

## Usage

```python
from content_core.config import get_extraction_config
from content_core.engine_config import EngineResolver

config = get_extraction_config()
resolver = EngineResolver(config)

# Resolve engines for a MIME type
engines = resolver.resolve("application/pdf")
# Returns: ['docling-vlm', 'docling', 'pymupdf'] based on ENV config

# With explicit override
engines = resolver.resolve("application/pdf", explicit="pymupdf")
# Returns: ['pymupdf']
```

## ENV Variables

```bash
# Per MIME type
CCORE_ENGINE_APPLICATION_PDF=docling-vlm,docling,pymupdf
CCORE_ENGINE_IMAGE=docling

# Per category
CCORE_ENGINE_DOCUMENTS=docling
CCORE_ENGINE_URLS=jina,firecrawl

# Legacy engine selection
CCORE_DOCUMENT_ENGINE=docling  # For all document types
CCORE_URL_ENGINE=jina          # For all URL types

# Fallback config
CCORE_FALLBACK_ENABLED=true
CCORE_FALLBACK_MAX_ATTEMPTS=3
CCORE_FALLBACK_ON_ERROR=warn
```

## Integration

- **Called by**: `content/extraction/router.py` to resolve engines
- **Uses**: `ProcessorRegistry` for auto-detection
- **Imported from**: `content_core.config` (get_extraction_config)
- **Options from**: `get_docling_options()`, `get_marker_options()`, `get_pymupdf_options()` in config.py

## Gotchas

- YAML configuration is no longer supported (v2.0)
- ENV variables use underscores instead of slashes/plus (e.g., `APPLICATION_PDF` not `application/pdf`)
- Engine chains are comma-separated in ENV vars
- `on_error="fail"` raises immediately without trying other engines
- `fatal_errors` list uses exception class names as strings
- Legacy config (`document_engine`/`url_engine`) is step 5, before auto-detect
- Engine options come from helper functions in config.py, not from config dict
