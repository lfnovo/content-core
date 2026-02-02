# Docling VLM Engine

Docling VLM uses Vision-Language Models for enhanced document understanding, providing better results for complex layouts, tables, and images.

## License

**MIT** - Commercial-friendly, no restrictions on use.

## Installation

```bash
# For local VLM inference (transformers backend)
pip install content-core[docling-vlm]

# For Apple Silicon optimized inference (MLX backend)
pip install content-core[docling-mlx]
```

## Inference Modes

### Local Inference

Run the VLM model directly on your machine:

```bash
export CCORE_DOCUMENT_ENGINE=docling-vlm
export CCORE_VLM_INFERENCE_MODE=local
export CCORE_VLM_BACKEND=auto  # auto, transformers, or mlx
export CCORE_VLM_MODEL=granite-docling  # or smol-docling
```

**Backend Selection:**
- `auto`: Automatically selects MLX on Apple Silicon, transformers otherwise
- `transformers`: Standard PyTorch/transformers backend
- `mlx`: Optimized for Apple Silicon (M1/M2/M3)

### Remote Inference

Offload processing to a GPU server running docling-serve:

```bash
export CCORE_DOCUMENT_ENGINE=docling-vlm
export CCORE_VLM_INFERENCE_MODE=remote
export CCORE_DOCLING_SERVE_URL=http://gpu-server:5001
export CCORE_DOCLING_SERVE_API_KEY=your-api-key  # optional
export CCORE_DOCLING_SERVE_TIMEOUT=120
```

**Running docling-serve:**

```bash
# Using Docker
docker run -p 5001:5001 ds4sd/docling-serve

# With GPU support
docker run --gpus all -p 5001:5001 ds4sd/docling-serve
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CCORE_DOCUMENT_ENGINE` | Set to `docling-vlm` | `auto` |
| `CCORE_VLM_INFERENCE_MODE` | `local` or `remote` | `local` |
| `CCORE_VLM_BACKEND` | `auto`, `transformers`, `mlx` | `auto` |
| `CCORE_VLM_MODEL` | `granite-docling`, `smol-docling` | `granite-docling` |
| `CCORE_DOCLING_SERVE_URL` | Remote endpoint | `http://localhost:5001` |
| `CCORE_DOCLING_SERVE_API_KEY` | API key | `null` |
| `CCORE_DOCLING_SERVE_TIMEOUT` | Timeout (seconds) | `120` |

### VLM Processing Options

| Variable | Description | Default |
|----------|-------------|---------|
| `CCORE_VLM_DO_OCR` | Enable OCR | `true` |
| `CCORE_VLM_OCR_ENGINE` | OCR engine | `easyocr` |
| `CCORE_VLM_TABLE_MODE` | Table extraction | `accurate` |
| `CCORE_VLM_DO_TABLE_STRUCTURE` | Extract table structure | `true` |
| `CCORE_VLM_DO_CODE_ENRICHMENT` | Enhance code blocks | `false` |
| `CCORE_VLM_DO_FORMULA_ENRICHMENT` | Enhance formulas | `false` |
| `CCORE_VLM_INCLUDE_IMAGES` | Include images | `true` |
| `CCORE_VLM_DO_PICTURE_CLASSIFICATION` | Classify images | `false` |
| `CCORE_VLM_DO_PICTURE_DESCRIPTION` | Generate descriptions | `false` |

### YAML Configuration

```yaml
extraction:
  document_engine: docling-vlm
  docling:
    output_format: markdown
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
```

### Python

```python
from content_core.config import (
    set_document_engine,
    set_vlm_inference_mode,
    set_vlm_backend,
    set_vlm_model,
    set_vlm_remote_url,
)

# Local inference
set_document_engine("docling-vlm")
set_vlm_inference_mode("local")
set_vlm_backend("mlx")  # Apple Silicon

# Remote inference
set_document_engine("docling-vlm")
set_vlm_inference_mode("remote")
set_vlm_remote_url("http://gpu-server:5001")
```

## Performance

| Mode | Speed | Memory | GPU Required |
|------|-------|--------|--------------|
| Local (MLX) | ~30-60s/doc | ~4GB | No (uses Apple Silicon) |
| Local (transformers) | ~60-120s/doc | ~8GB | Recommended |
| Remote | Depends on server | Low client | Server-side |

## When to Use

**Use VLM when:**
- Documents have complex layouts (multi-column, mixed content)
- Better table extraction is needed (merged cells, nested)
- Documents contain charts, diagrams, or figures
- Scientific papers with equations and figures
- High accuracy is more important than speed

**Don't use when:**
- Speed is priority (use `pymupdf4llm` or `docling`)
- Simple text documents
- Limited hardware resources

## Platform-Specific Notes

### macOS (Apple Silicon)

```bash
# Use MLX backend for best performance
pip install content-core[docling-mlx]
export CCORE_VLM_BACKEND=mlx
```

**Known Issues:**
- First run downloads ~258MB model
- MPS produces incorrect output for picture descriptions (use CPU)

### Linux

```bash
# Use transformers backend with CUDA
pip install content-core[docling-vlm]
export CCORE_VLM_BACKEND=transformers
```

**GPU Recommended:** VLM inference is slow without GPU acceleration.

### Windows

Same as Linux. GPU recommended for reasonable performance.

## Gotchas

1. **Model download:** First run downloads ~258MB model
2. **Memory usage:** Requires ~4-8GB RAM
3. **Speed:** Much slower than standard Docling
4. **Picture description issues:** VlmPipeline doesn't support picture description well; use standard `docling` engine with `do_picture_description=true` instead
5. **Remote mode requires httpx:** Install with `pip install httpx`

## Checking Availability

```python
from content_core.processors.docling_vlm import (
    DOCLING_VLM_LOCAL_AVAILABLE,
    HTTPX_AVAILABLE,
)

if DOCLING_VLM_LOCAL_AVAILABLE:
    print("Local VLM inference available")
if HTTPX_AVAILABLE:
    print("Remote VLM inference available")
```
