# CLI Reference

Content Core provides three command-line tools: `ccore`, `cclean`, and `csum`.

## Zero-Install Usage

Use `uvx` to run without installing:

```bash
uvx --from "content-core" ccore https://example.com
uvx --from "content-core" cclean "messy content"
uvx --from "content-core" csum article.txt
```

## ccore - Extract Content

Extracts content from URLs, files, or text.

### Usage

```bash
ccore [-f|--format FORMAT] [-d|--debug] [content]
```

### Options

| Option | Description |
|--------|-------------|
| `-f`, `--format` | Output format: `text` (default), `json`, `xml` |
| `-d`, `--debug` | Enable debug logging |
| `content` | URL, file path, or text. Reads from stdin if omitted |

### Examples

```bash
# Extract from URL
ccore https://example.com

# Extract from file
ccore document.pdf

# Output as JSON
ccore -f json https://example.com

# Output as XML
ccore --format xml document.pdf

# From stdin
echo "Sample text" | ccore

# With debug logging
ccore -d https://example.com
```

### Supported Sources

- **URLs**: Any web page
- **Documents**: PDF, DOCX, XLSX, PPTX, HTML, Markdown, EPUB
- **Media**: MP4, AVI, MOV, MP3, WAV, M4A
- **Images**: PNG, JPEG, TIFF (OCR)
- **Text**: Plain text, JSON, XML

---

## cclean - Clean Content

Cleans content by removing unnecessary formatting, spaces, or artifacts.

### Usage

```bash
cclean [-d|--debug] [content]
```

### Options

| Option | Description |
|--------|-------------|
| `-d`, `--debug` | Enable debug logging |
| `content` | Text, URL, file path, JSON, or XML. Reads from stdin if omitted |

### Examples

```bash
# Clean text
cclean "  messy   text   with   spaces  "

# Clean from URL
cclean https://example.com

# Clean from file
cclean document.txt

# From stdin
echo '{"content": "  messy  "}' | cclean

# Pipeline
ccore document.pdf | cclean
```

---

## csum - Summarize Content

Summarizes content with optional context for style guidance.

### Usage

```bash
csum [--context "context"] [-d|--debug] [content]
```

### Options

| Option | Description |
|--------|-------------|
| `--context` | Summary style/context (e.g., "bullet points", "explain to a child") |
| `-d`, `--debug` | Enable debug logging |
| `content` | Text, URL, file path, JSON, or XML. Reads from stdin if omitted |

### Examples

```bash
# Basic summary
csum article.txt

# With context
csum --context "bullet points" article.txt
csum --context "explain to a child" technical_paper.pdf
csum --context "executive summary" report.pdf

# From URL
csum https://example.com/article

# From stdin
cat long_document.txt | csum --context "one sentence"

# Pipeline
ccore document.pdf | csum --context "key takeaways"
```

### Summary Contexts

| Context | Description |
|---------|-------------|
| `bullet points` | Key points as bullet list |
| `one sentence` | Single sentence summary |
| `explain to a child` | Simple language |
| `executive summary` | Business-focused overview |
| `technical summary` | Technical details preserved |
| `action items` | Extract actionable items |

---

## Environment Variables

Configure CLI behavior with environment variables:

```bash
# Extraction engines
export CCORE_DOCUMENT_ENGINE=docling
export CCORE_URL_ENGINE=auto

# API keys
export OPENAI_API_KEY=your-key
export FIRECRAWL_API_KEY=your-key

# Audio processing
export CCORE_AUDIO_CONCURRENCY=5
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (invalid input, API failure, etc.) |

## Pipelines

Combine CLI tools in pipelines:

```bash
# Extract and summarize
ccore document.pdf | csum --context "bullet points"

# Extract, clean, and summarize
ccore messy_document.pdf | cclean | csum

# Process multiple files
for f in *.pdf; do ccore "$f" > "${f%.pdf}.txt"; done
```
