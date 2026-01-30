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
CCORE_URL_ENGINE=auto       # auto, simple, firecrawl, jina, crawl4ai
```

### Engine Selection Environment Variables

Content Core supports environment variable overrides for extraction engines, useful for deployment scenarios:

- **`CCORE_DOCUMENT_ENGINE`**: Override document engine (`auto`, `simple`, `docling`)
- **`CCORE_URL_ENGINE`**: Override URL engine (`auto`, `simple`, `firecrawl`, `jina`, `crawl4ai`)
- **`FIRECRAWL_API_BASE_URL`**: Custom Firecrawl API URL for self-hosted instances (default: `https://api.firecrawl.dev`)

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
- **For URLs** (`url_engine`): Uses Firecrawl if `FIRECRAWL_API_KEY` is set, else Jina (optionally with `JINA_API_KEY`), else Crawl4AI if installed, else falls back to BeautifulSoup. You can also explicitly set it to `crawl4ai` for local, privacy-first scraping without API keys.
- **For files** (`document_engine`): Tries Docling extraction first (for robust document parsing), then falls back to simple extraction if needed.

You can override this behavior by specifying separate engines for documents and URLs in your config or function call, but `'auto'` is recommended for most users.

#### Docling Engine

Content Core supports an optional Docling engine for advanced document parsing. To enable Docling explicitly:

##### In YAML config
Add under the `extraction` section:
```yaml
extraction:
  document_engine: docling  # auto (default), simple, or docling
  url_engine: auto          # auto (default), simple, firecrawl, jina, or crawl4ai
  firecrawl:
    api_url: null           # Custom API URL for self-hosted Firecrawl (e.g., "http://localhost:3002")
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

# Use a self-hosted Firecrawl instance
from content_core.config import set_firecrawl_api_url
set_firecrawl_api_url("http://localhost:3002")

# Configure PyMuPDF OCR for scientific documents
set_pymupdf_ocr_enabled(True)
set_pymupdf_formula_threshold(2)  # Lower threshold for math-heavy docs
```

#### Self-Hosted Firecrawl

Content Core supports self-hosted Firecrawl instances for users who want to run their own web scraping infrastructure. This is useful for privacy, compliance, or high-volume scraping needs.

To use a self-hosted Firecrawl instance:

1. **Set up Firecrawl** - Follow the [official self-hosting guide](https://github.com/mendableai/firecrawl/blob/main/SELF_HOST.md) to deploy Firecrawl using Docker Compose or Kubernetes.

2. **Configure Content Core** - Point to your instance using one of these methods:

   ```bash
   # Environment variable
   export FIRECRAWL_API_BASE_URL="http://localhost:3002"
   ```

   ```yaml
   # YAML config (cc_config.yaml)
   extraction:
     firecrawl:
       api_url: "http://localhost:3002"
   ```

   ```python
   # Programmatic
   from content_core.config import set_firecrawl_api_url
   set_firecrawl_api_url("http://localhost:3002")
   ```

3. **Optional: Set API key** - If your self-hosted instance uses authentication, also set `FIRECRAWL_API_KEY`.

#### Crawl4AI Engine

Content Core supports Crawl4AI as an optional URL extraction engine for privacy-first, local web scraping without requiring external API keys.

##### Installation

To enable Crawl4AI, install with the optional dependency:

```bash
pip install content-core[crawl4ai]

# Install Playwright browsers (required for Crawl4AI)
python -m playwright install --with-deps
```

##### When to Use Crawl4AI

Use the Crawl4AI engine when you need:
- **Privacy-first scraping**: All processing happens locally without sending data to external APIs
- **No API key required**: Unlike Firecrawl and Jina, Crawl4AI doesn't require API credentials
- **JavaScript-heavy sites**: Crawl4AI uses Playwright for full browser rendering
- **Local development**: Ideal for development and testing without API costs
- **Cost optimization**: No per-request API charges

##### Configuration

**In YAML config:**
```yaml
extraction:
  url_engine: crawl4ai  # auto (default), simple, firecrawl, jina, or crawl4ai
```

**Programmatically in Python:**
```python
from content_core.config import set_url_engine

# Set URL engine to Crawl4AI
set_url_engine("crawl4ai")
```

**Per-execution override:**
```python
from content_core.content.extraction import extract_content

# Override URL engine for this specific URL
result = await extract_content({
    "url": "https://example.com",
    "url_engine": "crawl4ai"
})
print(result.content)
```

Or using `ProcessSourceInput`:
```python
from content_core.common.state import ProcessSourceInput
from content_core.content.extraction import extract_content

input = ProcessSourceInput(
    url="https://example.com",
    url_engine="crawl4ai"
)
result = await extract_content(input)
print(result.content)
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

## Audio Processing Configuration

Content Core optimizes audio and video file processing by using parallel transcription of audio segments. This feature is particularly beneficial for long-form content like podcasts, lectures, or long videos.

### How It Works

1. **Automatic Segmentation**: Audio files longer than 10 minutes are automatically split into segments
2. **Parallel Transcription**: Multiple segments are transcribed concurrently using OpenAI Whisper
3. **Concurrency Control**: A semaphore limits the number of simultaneous API calls to prevent rate limiting
4. **Result Assembly**: Transcriptions are joined in the correct order to produce the complete transcript

### Configuration

#### Via YAML Configuration

Add to your `cc_config.yaml` or custom configuration file:

```yaml
extraction:
  audio:
    concurrency: 3  # Number of concurrent transcriptions (1-10, default: 3)
```

#### Via Environment Variable

Set in your `.env` file or system environment:

```plaintext
CCORE_AUDIO_CONCURRENCY=5  # Process 5 segments simultaneously
```

The environment variable takes precedence over the YAML configuration.

#### Programmatically in Python

```python
from content_core.config import set_audio_concurrency

# Override audio concurrency for the current session
set_audio_concurrency(5)

# Now process audio with the new setting
result = await cc.extract({"file_path": "long_podcast.mp3"})
```

### Performance Considerations

**Choosing the Right Concurrency Level:**

- **1-2 concurrent**: Conservative approach
  - Best for: API rate limits, cost management, batch processing
  - Processing time: Slower, but more reliable

- **3-5 concurrent** (recommended): Balanced approach
  - Best for: Most use cases, moderate file lengths
  - Processing time: Good balance between speed and stability

- **6-10 concurrent**: Aggressive approach
  - Best for: Very long files (>1 hour), premium API tiers
  - Processing time: Fastest, but higher risk of rate limits
  - Note: May result in higher API costs

**Example Processing Times** (approximate, for a 60-minute audio file):
- Concurrency 1: ~15-20 minutes
- Concurrency 3: ~5-7 minutes
- Concurrency 10: ~2-3 minutes

### Validation and Error Handling

Content Core validates the concurrency setting and provides safe defaults:

- **Valid range**: 1-10 concurrent transcriptions
- **Invalid values**: Automatically fall back to default (3) with a warning logged
- **Invalid types**: Non-integer values are rejected with a warning

Example warning when using invalid value:
```
WARNING: Invalid CCORE_AUDIO_CONCURRENCY: '15'. Must be between 1 and 10. Using default from config.
```

### Use Cases

**Podcasts and Long Interviews:**
```python
from content_core.config import set_audio_concurrency
import content_core as cc

# For a 2-hour podcast, use higher concurrency
set_audio_concurrency(7)
result = await cc.extract({"file_path": "podcast_episode_120min.mp3"})
```

**Batch Processing:**
```python
from content_core.config import set_audio_concurrency
import content_core as cc

# For processing multiple files sequentially, use lower concurrency
# to avoid rate limits across all files
set_audio_concurrency(2)

for audio_file in audio_files:
    result = await cc.extract({"file_path": audio_file})
    # Process result...
```

**Video Transcription:**
```python
import content_core as cc

# Videos are processed the same way - audio is extracted first, then transcribed
result = await cc.extract({"file_path": "conference_talk.mp4"})
print(result.content)  # Full transcript
```

## Custom Audio Model Configuration

Content Core allows you to override the default speech-to-text model at runtime, enabling you to choose different AI providers and models based on your specific needs (language support, cost, accuracy, etc.).

### Overview

By default, audio and video files are transcribed using the model configured in `models_config.yaml` (typically OpenAI Whisper-1). You can override this on a per-call basis by specifying both `audio_provider` and `audio_model` parameters.

**Key Features:**
- ✅ **Runtime flexibility**: Choose different models for different use cases
- ✅ **Backward compatible**: Existing code works unchanged
- ✅ **Multiple providers**: Support for any provider supported by Esperanto
- ✅ **Automatic fallback**: Graceful handling of invalid configurations

### Basic Usage

```python
from content_core.common import ProcessSourceInput
import content_core as cc

# Use custom audio model for transcription
result = await cc.extract(ProcessSourceInput(
    file_path="interview.mp3",
    audio_provider="openai",
    audio_model="whisper-1"
))

print(result.content)  # Transcribed text using specified model
```

### Supported Providers

Content Core uses the Esperanto library for AI model abstraction, which supports multiple providers:

- **OpenAI**: `provider="openai"`, models: `whisper-1`
- **Google**: `provider="google"`, models: `chirp` (if available)
- **Other providers**: Any provider supported by Esperanto

Check the [Esperanto documentation](https://github.com/yourusername/esperanto) for the full list of supported providers and models.

### Use Cases

**Multilingual Transcription:**
```python
from content_core.common import ProcessSourceInput
import content_core as cc

# Use a model optimized for a specific language
result = await cc.extract(ProcessSourceInput(
    file_path="spanish_interview.mp3",
    audio_provider="openai",
    audio_model="whisper-1"  # Whisper supports 99 languages
))
```

**Cost Optimization:**
```python
from content_core.common import ProcessSourceInput
import content_core as cc

# Use different models based on quality requirements
# For high-value content, use premium model
premium_result = await cc.extract(ProcessSourceInput(
    file_path="important_meeting.mp3",
    audio_provider="openai",
    audio_model="whisper-1"
))

# For casual content, use default or cost-effective model
casual_result = await cc.extract(ProcessSourceInput(
    file_path="casual_recording.mp3"
    # No custom params = uses default configured model
))
```

**Video Transcription with Custom Model:**
```python
from content_core.common import ProcessSourceInput
import content_core as cc

# Custom model works for video files too (audio is extracted automatically)
result = await cc.extract(ProcessSourceInput(
    file_path="conference_presentation.mp4",
    audio_provider="openai",
    audio_model="whisper-1"
))
```

### Parameter Requirements

Both `audio_provider` and `audio_model` must be specified together:

```python
# ✅ CORRECT: Both parameters provided
result = await cc.extract(ProcessSourceInput(
    file_path="audio.mp3",
    audio_provider="openai",
    audio_model="whisper-1"
))

# ✅ CORRECT: Neither parameter (uses default)
result = await cc.extract(ProcessSourceInput(
    file_path="audio.mp3"
))

# ⚠️ WARNING: Only one parameter (logs warning, uses default)
result = await cc.extract(ProcessSourceInput(
    file_path="audio.mp3",
    audio_provider="openai"  # Missing audio_model
))
# Logs: "audio_provider provided without audio_model. Both must be specified together. Falling back to default model."
```

### Error Handling

Content Core gracefully handles invalid model configurations:

**Invalid Provider:**
```python
result = await cc.extract(ProcessSourceInput(
    file_path="audio.mp3",
    audio_provider="invalid_provider",
    audio_model="whisper-1"
))
# Logs error and falls back to default model
# Transcription continues successfully
```

**Invalid Model Name:**
```python
result = await cc.extract(ProcessSourceInput(
    file_path="audio.mp3",
    audio_provider="openai",
    audio_model="nonexistent-model"
))
# Logs error and falls back to default model
# Transcription continues successfully
```

**Error Message Example:**
```
ERROR: Failed to create custom audio model 'invalid_provider/whisper-1': Unsupported provider.
Check that the provider and model are supported by Esperanto. Falling back to default model.
```

### Concurrency Control

Custom audio models respect the same concurrency limits as the default model (configured via `CCORE_AUDIO_CONCURRENCY` or `set_audio_concurrency()`). This ensures consistent API rate limit handling regardless of which model you use.

```python
from content_core.config import set_audio_concurrency
from content_core.common import ProcessSourceInput
import content_core as cc

# Set concurrency for all transcriptions (default and custom models)
set_audio_concurrency(5)

# Both use the same concurrency limit
default_result = await cc.extract(ProcessSourceInput(file_path="audio1.mp3"))
custom_result = await cc.extract(ProcessSourceInput(
    file_path="audio2.mp3",
    audio_provider="openai",
    audio_model="whisper-1"
))
```

### Backward Compatibility

All existing code continues to work without any changes:

```python
import content_core as cc

# Old code (no custom params) - still works perfectly
result = await cc.extract("audio.mp3")
result = await cc.extract({"file_path": "audio.mp3"})

# New capability (optional custom params)
from content_core.common import ProcessSourceInput
result = await cc.extract(ProcessSourceInput(
    file_path="audio.mp3",
    audio_provider="openai",
    audio_model="whisper-1"
))
```

### Troubleshooting

**Issue**: "Both audio_provider and audio_model must be specified together"
- **Solution**: Provide both parameters or neither. Don't specify just one.

**Issue**: "Failed to create custom audio model"
- **Solution**: Verify the provider and model are supported by Esperanto. Check your API keys are configured correctly.

**Issue**: Custom model seems to be ignored
- **Solution**: Ensure you're using `ProcessSourceInput` class (not plain dict) when passing custom parameters.

## Timeout Configuration

Content Core uses the Esperanto library for AI model interactions and provides configurable timeout settings to prevent requests from hanging indefinitely. Timeouts are essential for reliable processing, especially with long-running operations like audio transcription or large document processing.

### Understanding Timeouts

Timeouts define the maximum time (in seconds) that Content Core will wait for an AI model operation to complete before timing out. Different operations have different timeout requirements:

- **Speech-to-Text (audio transcription)**: Requires longer timeouts due to large file processing
- **Language Models (text generation)**: Requires moderate timeouts for content cleanup and summarization
- **Complex operations**: Operations processing large content (8000+ tokens) need extended timeouts

### Default Timeout Values

Content Core includes optimized timeout defaults for each model type:

| Model Type | Timeout | Use Case |
|------------|---------|----------|
| **speech_to_text** | 3600 seconds (1 hour) | Very long audio files, conference recordings |
| **default_model** | 300 seconds (5 minutes) | General language model operations |
| **cleanup_model** | 600 seconds (10 minutes) | Large content cleanup (8000 max tokens) |
| **summary_model** | 300 seconds (5 minutes) | Content summarization |

### Configuration Methods

Esperanto (and Content Core) support multiple timeout configuration approaches with clear priority ordering:

#### 1. Config Files (Highest Priority)

Timeouts are defined in `cc_config.yaml` or `models_config.yaml`:

```yaml
speech_to_text:
  provider: openai
  model_name: whisper-1
  timeout: 3600  # 1 hour for very long audio files

default_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0.5
    max_tokens: 2000
    timeout: 300  # 5 minutes

cleanup_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 8000
    timeout: 600  # 10 minutes for large content

summary_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 2000
    timeout: 300  # 5 minutes
```

**Note**: For speech-to-text models, `timeout` is a top-level parameter (not under `config`). For language models, `timeout` goes inside the `config` dictionary.

#### 2. Environment Variables (Fallback Defaults)

Set global timeout defaults that apply to all models of a given type when a timeout is not defined in the YAML configuration:

```bash
# Language model timeout default (applies when config files omit a timeout)
export ESPERANTO_LLM_TIMEOUT=300

# Speech-to-text timeout default (applies when config files omit a timeout)
export ESPERANTO_STT_TIMEOUT=3600
```

Add to your `.env` file:

```plaintext
# Override language model timeout globally (fallback default)
ESPERANTO_LLM_TIMEOUT=300

# Override speech-to-text timeout globally (fallback default)
ESPERANTO_STT_TIMEOUT=3600
```

### Validation and Constraints

**Valid Range:** 1 to 3600 seconds (1 hour maximum)

**Type Requirements:** Must be an integer number of seconds.

Examples of **invalid** timeouts that will raise errors:
- String values: `"30"`
- Negative values: `-1`
- Zero: `0`
- Exceeds maximum: `4000`

### Use Case Examples

#### Production Deployment

For production environments with strict reliability requirements:

```yaml
# Production cc_config.yaml
speech_to_text:
  provider: openai
  model_name: whisper-1
  timeout: 1800  # 30 minutes - sufficient for most podcasts

default_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    timeout: 120  # 2 minutes - faster failures for user-facing features

cleanup_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    timeout: 300  # 5 minutes - balance between reliability and patience

summary_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    timeout: 120  # 2 minutes - quick summaries
```

#### Development Environment

For development with generous timeouts for debugging:

```yaml
# Development cc_config.yaml
speech_to_text:
  timeout: 3600  # 1 hour - no rush during development

default_model:
  config:
    timeout: 600  # 10 minutes - plenty of time to debug

cleanup_model:
  config:
    timeout: 900  # 15 minutes

summary_model:
  config:
    timeout: 600  # 10 minutes
```

#### Batch Processing

For processing large batches with maximum timeouts:

```bash
# Set environment variables for batch jobs
export ESPERANTO_LLM_TIMEOUT=600     # 10 minutes per document
export ESPERANTO_STT_TIMEOUT=3600    # 1 hour per audio file
```

### Troubleshooting Timeouts

**Issue**: "Request timed out after N seconds"
- **Solution**: Increase the timeout for the specific model type in your config file
- **Check**: Verify your API keys are valid and the service is responding
- **Consider**: Breaking large content into smaller chunks

**Issue**: Timeout seems to be ignored
- **Solution**: Check configuration priority - config file overrides environment variables
- **Verify**: Ensure the timeout value is within the valid range (1-3600)
- **Check**: Look for YAML syntax errors in your config file

**Issue**: Different timeout behavior across environments
- **Solution**: Use explicit config files instead of relying on environment variables
- **Best practice**: Commit `cc_config.yaml` to version control for consistency

### Best Practices

1. **Start Conservative**: Begin with moderate timeouts and increase only if needed
2. **Monitor Actual Duration**: Log actual operation times to set realistic timeouts
3. **Environment-Specific**: Use different timeouts for development vs production
4. **Consider API Limits**: Higher timeouts don't help if you hit API rate limits
5. **Balance Reliability**: Very long timeouts may hide underlying issues

### Related Configuration

Timeouts work in conjunction with other performance settings:

- **Audio Concurrency** (`CCORE_AUDIO_CONCURRENCY`): Controls parallel transcription, affects total processing time
- **Max Tokens** (`max_tokens` in config): Affects how much content the model processes
- **Temperature** (`temperature` in config): Affects generation quality and potentially speed

For more details on Esperanto timeout configuration, see the [Esperanto Timeout Documentation](https://github.com/lfnovo/esperanto/blob/main/docs/advanced/timeout-configuration.md).

## Retry Configuration

Content Core includes automatic retry logic for handling transient failures in external operations. Built on the [tenacity](https://tenacity.readthedocs.io/) library, retries use exponential backoff with jitter to gracefully handle temporary issues like network timeouts, API rate limits, and service unavailability.

### How It Works

When an external operation fails with a retryable error (network timeout, connection error, API error), Content Core automatically retries the operation with increasing delays between attempts. The backoff uses randomized exponential delays to prevent thundering herd problems when multiple requests fail simultaneously.

### Supported Operation Types

| Operation Type | Default Retries | Base Delay | Max Delay | Use Cases |
|---------------|-----------------|------------|-----------|-----------|
| `youtube` | 5 | 2s | 60s | Video title/transcript fetching (YouTube has aggressive rate limiting) |
| `url_api` | 3 | 1s | 30s | Jina, Firecrawl, Crawl4AI API extraction |
| `url_network` | 3 | 0.5s | 10s | HEAD requests, BeautifulSoup fetching |
| `audio` | 3 | 2s | 30s | Speech-to-text API calls |
| `llm` | 3 | 1s | 30s | LLM API calls (cleanup, summary) |
| `download` | 3 | 1s | 15s | Remote file downloads |

### Configuration Methods

#### Via YAML Configuration

Add to your `cc_config.yaml`:

```yaml
retry:
  youtube:
    max_attempts: 5      # Number of retry attempts
    base_delay: 2        # Base delay in seconds
    max_delay: 60        # Maximum delay between retries
  url_api:
    max_attempts: 3
    base_delay: 1
    max_delay: 30
  url_network:
    max_attempts: 3
    base_delay: 0.5
    max_delay: 10
  audio:
    max_attempts: 3
    base_delay: 2
    max_delay: 30
  llm:
    max_attempts: 3
    base_delay: 1
    max_delay: 30
  download:
    max_attempts: 3
    base_delay: 1
    max_delay: 15
```

#### Via Environment Variables

Override retry settings using environment variables with the pattern `CCORE_{TYPE}_{PARAM}`:

```bash
# YouTube retry settings
CCORE_YOUTUBE_MAX_RETRIES=10     # Max retry attempts (1-20)
CCORE_YOUTUBE_BASE_DELAY=3       # Base delay in seconds (0.1-60)
CCORE_YOUTUBE_MAX_DELAY=120      # Max delay in seconds (1-300)

# URL API retry settings (for Jina, Firecrawl, Crawl4AI)
CCORE_URL_API_MAX_RETRIES=5
CCORE_URL_API_BASE_DELAY=2
CCORE_URL_API_MAX_DELAY=60

# URL network retry settings (for BeautifulSoup, HEAD requests)
CCORE_URL_NETWORK_MAX_RETRIES=5
CCORE_URL_NETWORK_BASE_DELAY=1
CCORE_URL_NETWORK_MAX_DELAY=20

# Audio transcription retry settings
CCORE_AUDIO_MAX_RETRIES=5
CCORE_AUDIO_BASE_DELAY=3
CCORE_AUDIO_MAX_DELAY=60

# LLM retry settings (cleanup, summary)
CCORE_LLM_MAX_RETRIES=5
CCORE_LLM_BASE_DELAY=2
CCORE_LLM_MAX_DELAY=60

# Download retry settings
CCORE_DOWNLOAD_MAX_RETRIES=5
CCORE_DOWNLOAD_BASE_DELAY=2
CCORE_DOWNLOAD_MAX_DELAY=30
```

Environment variables take precedence over YAML configuration.

### Validation and Constraints

**Valid Ranges (for environment variable overrides):**
- `max_retries`: 1-20 attempts
- `base_delay`: 0.1-60 seconds
- `max_delay`: 1-300 seconds

Invalid environment variable values are ignored with a warning, and the system falls back to YAML or defaults. YAML configuration values are used as-is and must be valid.

### Behavior After Retries Exhausted

When all retry attempts are exhausted, Content Core maintains backward compatibility:
- Functions return `None` or empty content (not exceptions)
- Errors are logged with detailed information
- Processing continues for remaining operations

This ensures that a single transient failure doesn't crash your entire pipeline.

### Logging

Retry attempts are logged at WARNING level with details:
```
WARNING: Retry 2 for _fetch_video_title: ClientError: Connection timeout
```

When all retries are exhausted:
```
ERROR: All 5 retries exhausted for _fetch_video_title: ClientError: Service unavailable
```

### Use Cases

**High-Reliability Batch Processing:**
```bash
# Increase retries for batch jobs where reliability is critical
CCORE_YOUTUBE_MAX_RETRIES=10
CCORE_URL_API_MAX_RETRIES=5
CCORE_AUDIO_MAX_RETRIES=5
```

**Fast-Fail Development:**
```bash
# Reduce retries for faster feedback during development
CCORE_YOUTUBE_MAX_RETRIES=2
CCORE_URL_API_MAX_RETRIES=1
CCORE_AUDIO_MAX_RETRIES=1
```

**Rate-Limited APIs:**
```bash
# Increase delays for APIs with strict rate limits
CCORE_URL_API_BASE_DELAY=5
CCORE_URL_API_MAX_DELAY=120
```

### Technical Details

The retry decorators are available for advanced use in custom code:

```python
from content_core.common.retry import (
    retry_youtube,
    retry_url_api,
    retry_url_network,
    retry_audio_transcription,
    retry_llm,
    retry_download,
)

# Use decorators on your own functions
@retry_url_api(max_attempts=5, base_delay=2, max_delay=60)
async def my_custom_api_call():
    # Your API call logic here
    pass
```

## Proxy Configuration

Content Core supports HTTP/HTTPS proxy configuration through standard environment variables. This approach is consistent with most HTTP clients and the Esperanto library.

### Configuration

Set the standard proxy environment variables:

```bash
# In your .env file or shell environment
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080

# With authentication
HTTP_PROXY=http://user:password@proxy.example.com:8080

# Bypass proxy for specific hosts
NO_PROXY=localhost,127.0.0.1,internal.example.com
```

That's it! Content Core automatically uses these environment variables for all network requests.

### How It Works

Content Core uses `trust_env=True` with aiohttp sessions, which enables automatic reading of proxy settings from standard environment variables. This is the same approach used by most Python HTTP libraries and provides consistent behavior across your entire application.

**Supported Services:**

| Service | Notes |
|---------|-------|
| **aiohttp requests** | URL extraction, HEAD checks, downloads |
| **YouTube (pytubefix)** | Video info, captions (uses requests internally) |
| **YouTube (transcript-api)** | Transcript fetching (uses requests internally) |
| **Crawl4AI** | Bridges HTTP_PROXY to ProxyConfig automatically |
| **Jina** | URL extraction API |
| **Esperanto (LLM/STT)** | Language model and speech-to-text requests |

**Note:** Firecrawl does not support client-side proxy configuration. Configure proxy on the Firecrawl server side instead.

### Use Cases

#### Corporate Environment

```bash
# In .env file
HTTP_PROXY=http://corporate-proxy.internal:8080
HTTPS_PROXY=http://corporate-proxy.internal:8080
NO_PROXY=localhost,127.0.0.1,*.internal.corp
```

```python
import content_core as cc

# All requests automatically use corporate proxy
result = await cc.extract("https://external-site.com/article")
```

#### Temporary Proxy for a Script

```bash
# Set proxy just for this command
HTTP_PROXY=http://proxy:8080 HTTPS_PROXY=http://proxy:8080 python my_script.py
```

### Troubleshooting

**Issue**: Requests timing out through proxy
- **Solution**: Verify proxy URL is correct and accessible
- **Check**: Ensure proxy allows the target hosts

**Issue**: Authentication failures
- **Solution**: URL-encode special characters in password
- **Example**: `http://user:p%40ssword@proxy:8080` for password `p@ssword`

**Issue**: Proxy not being used
- **Verify**: Environment variables are exported in current shell (`echo $HTTP_PROXY`)
- **Check**: Variable names are uppercase (`HTTP_PROXY`, not `http_proxy`)
- **Debug**: Enable debug logging to confirm requests are being made

**Issue**: SSL/TLS errors through proxy
- **Solution**: Ensure proxy supports HTTPS connections
- **Check**: Proxy certificate configuration (you may need to trust the proxy's CA)

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
