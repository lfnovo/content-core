# Docling VLM Pipeline Implementation Summary

## Overview

This document summarizes the implementation of VLM (Vision-Language Model) powered document extraction for content-core, providing enhanced document understanding through Docling's VlmPipeline.

## What Was Implemented

### 1. Core Type Definitions (`src/content_core/common/types.py`)

Added new type literals for VLM configuration:
```python
DocumentEngine = Literal["auto", "simple", "docling", "docling-vlm"]
VlmInferenceMode = Literal["local", "remote"]
VlmBackend = Literal["auto", "transformers", "mlx"]
VlmModel = Literal["granite-docling", "smol-docling"]
```

### 2. State Model Updates (`src/content_core/common/state.py`)

Added VLM override fields to `ProcessSourceState` and `ProcessSourceInput`:
- `vlm_inference_mode`: Override inference mode (local/remote)
- `vlm_backend`: Override backend (auto/transformers/mlx)
- `vlm_remote_url`: Override remote docling-serve URL

### 3. Configuration (`src/content_core/config.py` & `cc_config.yaml`)

#### New Configuration Section in YAML
```yaml
docling:
  vlm:
    inference_mode: local
    local:
      backend: auto
      model: granite-docling
    remote:
      url: http://localhost:5001
      api_key: null
      timeout: 120
    options:
      do_ocr: true
      ocr_engine: easyocr
      table_mode: accurate
      do_table_structure: true
      do_code_enrichment: false
      do_formula_enrichment: false
      include_images: true
      do_picture_classification: false
      do_picture_description: false
```

#### New Functions Added
**Getters:**
- `get_vlm_inference_mode()` - returns "local" or "remote"
- `get_vlm_backend()` - returns "auto", "transformers", or "mlx"
- `get_vlm_model()` - returns "granite-docling" or "smol-docling"
- `get_vlm_remote_url()` - returns docling-serve URL
- `get_vlm_remote_api_key()` - returns API key (optional)
- `get_vlm_remote_timeout()` - returns timeout in seconds
- `get_vlm_options()` - returns dict of all processing options

**Setters:**
- `set_vlm_inference_mode(mode)`
- `set_vlm_backend(backend)`
- `set_vlm_model(model)`
- `set_vlm_remote_url(url)`
- `set_vlm_remote_timeout(timeout)`

### 4. VLM Processor (`src/content_core/processors/docling_vlm.py`)

New processor with:

**Availability Flags:**
- `DOCLING_VLM_LOCAL_AVAILABLE` - True if docling[vlm] is installed
- `DOCLING_VLM_MLX_AVAILABLE` - True if MLX is available (Apple Silicon)
- `HTTPX_AVAILABLE` - True if httpx is installed (for remote)

**Functions:**
- `_get_model_spec(model_name, backend)` - Gets model spec from docling
- `_detect_best_backend()` - Auto-detects MLX on Apple Silicon, else transformers
- `_detect_best_device()` - Auto-detects mps/cuda/cpu
- `extract_with_vlm_local(state)` - Local VLM extraction
- `extract_with_vlm_remote(state)` - Remote extraction via docling-serve
- `extract_with_docling_vlm(state)` - Router function

### 5. Graph Integration (`src/content_core/content/extraction/graph.py`)

- Added conditional import for `extract_with_docling_vlm`
- Added `"extract_docling_vlm"` node to workflow
- Updated `file_type_router_docling()` to handle `"docling-vlm"` engine

### 6. Dependencies (`pyproject.toml`)

Added optional dependency groups:
```toml
docling-vlm = ["docling[vlm]>=2.34.0", "httpx>=0.27.0"]
docling-mlx = ["docling[vlm]>=2.34.0", "mlx>=0.5.0", "httpx>=0.27.0"]
```

### 7. Unit Tests (`tests/unit/test_docling_vlm.py`)

40 test cases covering:
- `TestVLMConfigGetters` - Default values and env var overrides
- `TestVLMConfigSetters` - Validation of setter functions
- `TestVLMProcessorAvailability` - Import and availability checks
- `TestVLMBackendDetection` - Backend and device detection
- `TestVLMRemotePayload` - Remote API payload construction
- `TestVLMRouterSelection` - Engine selection in graph
- `TestVLMStateOverrides` - State-level config overrides
- `TestVLMOptions` - Processing options configuration
- `TestVLMLocalNotAvailable` - Error handling when dependencies missing

### 8. Integration Tests (`tests/integration/test_extraction.py`)

Added 4 integration tests:
- `test_extract_content_from_pdf_docling_vlm_local` - Local VLM extraction
- `test_extract_content_from_pdf_docling_vlm_remote` - Remote extraction with mock
- `test_docling_vlm_unsupported_type_fallback` - Fallback behavior
- `test_docling_vlm_config_override` - State-level overrides

### 9. Documentation Updates

- **README.md**: Installation options, VLM section, environment variables
- **CLAUDE.md**: Codebase structure, gotchas
- **docs/usage.md**: Comprehensive VLM configuration guide
- **processors/CLAUDE.md**: Processor documentation

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CCORE_DOCUMENT_ENGINE` | Set to `docling-vlm` | `auto` |
| `CCORE_VLM_INFERENCE_MODE` | `local` or `remote` | `local` |
| `CCORE_VLM_BACKEND` | `auto`, `transformers`, `mlx` | `auto` |
| `CCORE_VLM_MODEL` | `granite-docling`, `smol-docling` | `granite-docling` |
| `CCORE_DOCLING_SERVE_URL` | Remote endpoint | `http://localhost:5001` |
| `CCORE_DOCLING_SERVE_API_KEY` | API key | `null` |
| `CCORE_DOCLING_SERVE_TIMEOUT` | Timeout (seconds) | `120` |
| `CCORE_DOCLING_SERVE_PIPELINE` | Pipeline on server | `standard` |
| `CCORE_VLM_DO_OCR` | Enable OCR | `true` |
| `CCORE_VLM_OCR_ENGINE` | OCR engine | `easyocr` |
| `CCORE_VLM_TABLE_MODE` | `accurate` or `fast` | `accurate` |
| `CCORE_VLM_DO_TABLE_STRUCTURE` | Extract table structure | `true` |
| `CCORE_VLM_DO_CODE_ENRICHMENT` | Enhance code blocks | `false` |
| `CCORE_VLM_DO_FORMULA_ENRICHMENT` | Enhance formulas | `false` |
| `CCORE_VLM_INCLUDE_IMAGES` | Include images | `true` |
| `CCORE_VLM_DO_PICTURE_CLASSIFICATION` | Classify images | `false` |
| `CCORE_VLM_DO_PICTURE_DESCRIPTION` | Describe images | `false` |

## What Was Tested

### Unit Tests (All Passing - 40 tests)
```bash
uv run pytest tests/unit/test_docling_vlm.py -v
```

### Integration Tests (Require docling[vlm] installed)
```bash
uv run pytest tests/integration/test_extraction.py -v -k "vlm"
```

### CLI Testing
```bash
# Local VLM extraction
CCORE_DOCUMENT_ENGINE=docling-vlm ccore document.pdf

# Remote VLM extraction
CCORE_DOCUMENT_ENGINE=docling-vlm \
CCORE_VLM_INFERENCE_MODE=remote \
CCORE_DOCLING_SERVE_URL=http://server:5001 \
ccore document.pdf
```

## Known Issues / Limitations

### 1. VLM Pipeline on docling-serve Runs Asynchronously
When using `pipeline: "vlm"` on docling-serve, the server returns a task ID instead of results immediately. The current workaround uses `pipeline: "standard"` by default.

**Workaround:** Set `CCORE_DOCLING_SERVE_PIPELINE=standard` (default) for synchronous processing.

### 2. Model Spec Names Changed in Docling v2.68+
The model spec naming convention changed from `GRANITEDOCLING` to `GRANITEDOCLING_TRANSFORMERS`.

**Status:** Fixed in implementation.

### 3. Local VLM Requires Large Download
The granite-docling model (~258MB) downloads automatically on first use.

### 4. MLX Backend Only on Apple Silicon
MLX backend is only available on M1/M2/M3 Macs.

## Next Steps / Future Improvements

### 1. Async Task Polling for Remote VLM
Implement polling mechanism to wait for VLM pipeline results when using `pipeline: "vlm"` on docling-serve.

### 2. Progress Callbacks
Add progress callbacks for long-running VLM extractions.

### 3. Batch Processing Support
Support for processing multiple documents in a single remote request.

### 4. Caching
Cache model loading for local inference to improve performance on repeated calls.

### 5. GPU Memory Management
Add configuration for GPU memory limits when using transformers backend with CUDA.

### 6. Additional Models
Support for future VLM models as they become available in docling.

## Usage Examples

### Python - Local VLM
```python
import content_core as cc
from content_core.config import set_document_engine

set_document_engine("docling-vlm")
result = await cc.extract("document.pdf")
print(result.content)
```

### Python - Remote VLM
```python
from content_core.common.state import ProcessSourceInput
import content_core as cc

result = await cc.extract(ProcessSourceInput(
    file_path="document.pdf",
    document_engine="docling-vlm",
    vlm_inference_mode="remote",
    vlm_remote_url="http://gpu-server:5001"
))
print(result.content)
```

### CLI
```bash
# Quick test
CCORE_DOCUMENT_ENGINE=docling-vlm ccore test.pdf

# With all options
CCORE_DOCUMENT_ENGINE=docling-vlm \
CCORE_VLM_INFERENCE_MODE=remote \
CCORE_DOCLING_SERVE_URL=http://gpu-server:5001 \
CCORE_VLM_DO_CODE_ENRICHMENT=true \
CCORE_VLM_DO_FORMULA_ENRICHMENT=true \
ccore scientific_paper.pdf
```

## Files Modified/Created

| File | Action |
|------|--------|
| `src/content_core/common/types.py` | Modified |
| `src/content_core/common/state.py` | Modified |
| `src/content_core/config.py` | Modified |
| `src/content_core/cc_config.yaml` | Modified |
| `src/content_core/processors/docling_vlm.py` | **Created** |
| `src/content_core/content/extraction/graph.py` | Modified |
| `pyproject.toml` | Modified |
| `tests/unit/test_docling_vlm.py` | **Created** |
| `tests/integration/test_extraction.py` | Modified |
| `README.md` | Modified |
| `CLAUDE.md` | Modified |
| `docs/usage.md` | Modified |
| `src/content_core/processors/CLAUDE.md` | Modified |
| `docs/DOCLING_VLM_IMPLEMENTATION.md` | **Created** |
