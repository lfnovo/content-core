# Using the Content Core Library

> **Note:** As of vNEXT, the default extraction engine is `'auto'`. Content Core will automatically select the best extraction method based on your environment and available packages, with a smart fallback order for both URLs and files. For files/documents, `'auto'` tries Docling first (if installed with `pip install content-core[docling]`), then falls back to enhanced PyMuPDF extraction. You can override the engine if needed, but `'auto'` is recommended for most users.

This documentation explains how to configure and use the **Content Core** library in your projects. The library allows customization of AI model settings through a YAML file and environment variables.

## Environment Variable for Configuration

The library uses the `CCORE_MODEL_CONFIG_PATH` environment variable to locate the custom YAML configuration file. If this variable is not set or the specified file is not found, the library will fall back to internal default settings.

To set the environment variable, add the following line to your `.env` file or set it directly in your environment:

```
CCORE_MODEL_CONFIG_PATH=/path/to/your/models_config.yaml

# Optional: Override extraction engines
CCORE_DOCUMENT_ENGINE=auto  # auto, simple, docling
CCORE_URL_ENGINE=auto       # auto, simple, firecrawl, jina
```

### Engine Selection Environment Variables

Content Core supports environment variable overrides for extraction engines, useful for deployment scenarios:

- **`CCORE_DOCUMENT_ENGINE`**: Override document engine (`auto`, `simple`, `docling`)
- **`CCORE_URL_ENGINE`**: Override URL engine (`auto`, `simple`, `firecrawl`, `jina`)

These environment variables take precedence over configuration file settings and per-call overrides.

## YAML File Schema

The YAML configuration file defines the AI models that the library will use. The structure of the file is as follows:

- **speech_to_text**: Configuration for the speech-to-text model.
  - **provider**: Model provider (example: `openai`).
  - **model_name**: Model name (example: `whisper-1`).
- **default_model**: Configuration for the default language model.
  - **provider**: Model provider.
  - **model_name**: Model name.
  - **config**: Additional parameters like `temperature`, `top_p`, `max_tokens`.
- **cleanup_model**: Configuration for the content cleanup model.
  - **provider**: Model provider.
  - **model_name**: Model name.
  - **config**: Additional parameters.
- **summary_model**: Configuration for the summary model.
  - **provider**: Model provider.
  - **model_name**: Model name.
  - **config**: Additional parameters.

### Default YAML File

Here is the content of the default YAML file used by the library:

```yaml
speech_to_text:
  provider: openai
  model_name: whisper-1

default_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0.5
    top_p: 1
    max_tokens: 2000

cleanup_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 8000
    output_format: json

summary_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    top_p: 1
    max_tokens: 2000
```

## Customization

You can customize any aspect of the YAML file to suit your needs. Change the providers, model names, or configuration parameters as desired.

To simplify setup, we suggest copying the provided sample files:
- Copy `.env.sample` to `.env` and adjust the environment variables, including `CCORE_MODEL_CONFIG_PATH`.
- Copy `models_config.yaml.sample` to your desired location and modify it as needed.

This will allow you to quickly start with customized settings without needing to create the files from scratch.

### Extraction Engine Selection

By default, Content Core uses the `'auto'` engine for both document and URL extraction tasks. The logic is as follows:
- **For URLs** (`url_engine`): Uses Firecrawl if `FIRECRAWL_API_KEY` is set, else Jina if `JINA_API_KEY` is set, else falls back to BeautifulSoup.
- **For files** (`document_engine`): Tries Docling extraction first (for robust document parsing), then falls back to simple extraction if needed.

You can override this behavior by specifying separate engines for documents and URLs in your config or function call, but `'auto'` is recommended for most users.

#### Docling Engine

Content Core supports an optional Docling engine for advanced document parsing. To enable Docling explicitly:

##### In YAML config
Add under the `extraction` section:
```yaml
extraction:
  document_engine: docling  # auto (default), simple, or docling
  url_engine: auto          # auto (default), simple, firecrawl, or jina
  docling:
    output_format: html     # markdown | html | json
  pymupdf:
    enable_formula_ocr: false    # Enable OCR for formula-heavy pages
    formula_threshold: 3         # Min formulas per page to trigger OCR
    ocr_fallback: true          # Graceful fallback if OCR fails
```

##### Programmatically in Python
```python
from content_core.config import (
    set_document_engine, set_url_engine, set_docling_output_format,
    set_pymupdf_ocr_enabled, set_pymupdf_formula_threshold
)

# toggle document engine to Docling
set_document_engine("docling")

# toggle URL engine to Firecrawl
set_url_engine("firecrawl")

# pick format
set_docling_output_format("json")

# Configure PyMuPDF OCR for scientific documents
set_pymupdf_ocr_enabled(True)
set_pymupdf_formula_threshold(2)  # Lower threshold for math-heavy docs
```

#### Per-Execution Overrides
You can override the extraction engines and Docling output format on a per-call basis by including `document_engine`, `url_engine` and `output_format` in your input:

```python
from content_core.content.extraction import extract_content

# override document engine and format for this document
result = await extract_content({
    "file_path": "document.pdf",
    "document_engine": "docling",
    "output_format": "html"
})
print(result.content)

# override URL engine for this URL
result = await extract_content({
    "url": "https://example.com",
    "url_engine": "firecrawl"
})
print(result.content)
```

Or using `ProcessSourceInput`:

```python
from content_core.common.state import ProcessSourceInput
from content_core.content.extraction import extract_content

input = ProcessSourceInput(
    file_path="document.pdf",
    document_engine="docling",
    output_format="json"
)
result = await extract_content(input)
print(result.content)
```

## Enhanced PyMuPDF Processing

Content Core includes significant enhancements to PyMuPDF (the `simple` engine) for better PDF extraction, particularly for scientific documents and complex PDFs.

### Key Improvements

1. **Enhanced Quality Flags**: Automatic application of PyMuPDF quality flags for better text extraction:
   - `TEXT_PRESERVE_LIGATURES`: Better character rendering (eliminates encoding issues)
   - `TEXT_PRESERVE_WHITESPACE`: Improved spacing and layout preservation
   - `TEXT_PRESERVE_IMAGES`: Better integration of image-embedded text

2. **Mathematical Formula Enhancement**: Eliminates `<!-- formula-not-decoded -->` placeholders by properly extracting mathematical symbols and equations.

3. **Automatic Table Detection**: Tables are automatically detected and converted to markdown format for better LLM consumption.

4. **Selective OCR Enhancement**: Optional OCR support for formula-heavy pages when standard extraction is insufficient.

### Configuring OCR Enhancement

For scientific documents with heavy mathematical content, you can enable selective OCR:

#### Requirements
```bash
# Install Tesseract OCR (required for OCR functionality)
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
```

#### Configuration Options

**YAML Configuration:**
```yaml
extraction:
  pymupdf:
    enable_formula_ocr: true      # Enable OCR for formula-heavy pages
    formula_threshold: 3          # Minimum formulas per page to trigger OCR
    ocr_fallback: true           # Use standard extraction if OCR fails
```

**Python Configuration:**
```python
from content_core.config import (
    set_pymupdf_ocr_enabled, 
    set_pymupdf_formula_threshold,
    set_pymupdf_ocr_fallback
)

# Enable OCR for scientific documents
set_pymupdf_ocr_enabled(True)
set_pymupdf_formula_threshold(2)    # Lower threshold for math-heavy docs
set_pymupdf_ocr_fallback(True)      # Safe fallback if OCR fails
```

### Performance Considerations

- **Standard Processing**: No performance impact from quality improvements
- **OCR Processing**: ~1000x slower than standard extraction, but only triggers on formula-heavy pages
- **Smart Triggering**: OCR only activates when formula placeholder count exceeds threshold
- **Graceful Fallback**: If Tesseract is unavailable, falls back to enhanced standard extraction

### When to Enable OCR

Enable OCR enhancement for:
- Scientific papers with complex mathematical equations
- Technical documents with formulas that standard extraction can't handle
- Research papers where formula accuracy is critical

**Note**: The quality improvements (better character rendering, table detection) work automatically without requiring OCR or additional setup.

## File Type Detection

Content Core uses a pure Python implementation for file type detection, eliminating the need for system dependencies like libmagic. This ensures consistent behavior across all platforms (Windows, macOS, Linux).

### How It Works

The `FileDetector` class uses:
- **Binary signature matching** for formats like PDF, images, audio, and video files
- **Content analysis** for text-based formats (HTML, XML, JSON, YAML, CSV, Markdown)
- **ZIP structure detection** for modern document formats (DOCX, XLSX, PPTX, EPUB)

### Supported Formats

Content Core automatically detects and returns appropriate MIME types for:
- **Documents**: PDF, DOCX, XLSX, PPTX, ODT, ODS, ODP, RTF, EPUB
- **Images**: JPEG, PNG, GIF, BMP, WEBP, SVG, TIFF, ICO
- **Media**: MP4, AVI, MKV, MOV, MP3, WAV, OGG, FLAC, M4A
- **Text**: HTML, XML, JSON, YAML, CSV, Markdown, Plain text
- **Archives**: ZIP, TAR, GZ, BZ2, XZ

### Implementation Details

File detection is performed automatically when you call `extract_content()`. The detection:
- Reads only the necessary bytes (typically first 8KB) for performance
- Works regardless of file extension - detection is based on content
- Falls back to `text/plain` for unrecognized text files
- Returns `application/octet-stream` for binary files that don't match known signatures

This pure Python approach means:
- No installation headaches on different platforms
- Consistent behavior in all environments (local, Docker, serverless)
- Easy debugging and customization if needed
- No binary dependencies or system library conflicts

## Support

If you have questions or encounter issues while using the library, open an issue in the repository or contact the support team.
