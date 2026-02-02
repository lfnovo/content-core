# Raycast Extension

Content Core's Raycast extension provides seamless content extraction and summarization directly from your Raycast interface. With smart auto-detection and intuitive commands, you can process URLs, documents, videos, and more without leaving your workflow.

## Installation

### From Raycast Store (Recommended)
1. Open Raycast
2. Search for "Content Core" 
3. Click "Install" on the extension by `luis_novo`
4. Configure your API keys in preferences

### Manual Installation (Development)
1. Download or clone this repository
2. Open Raycast
3. Type "Import Extension"
4. Select the `raycast-content-core` folder
5. The extension will be built and imported

## Commands

### 1. Extract Content
**Smart content extraction with full interface**

- **Usage:** Type "Extract Content" in Raycast
- **Input:** Any URL or file path
- **Features:**
  - Auto-detects URLs vs file paths
  - Real-time type detection with visual feedback
  - Multiple output formats (Text, JSON, XML)
  - Drag & drop file support
  - Full results view with metadata

**Example:**
```
https://example.com/article
/Users/you/document.pdf
```

### 2. Summarize Content  
**AI-powered summarization with customizable styles**

- **Usage:** Type "Summarize Content" in Raycast
- **Input:** Any URL or file path
- **Features:**
  - Auto-detects URLs vs file paths
  - 9 different summary styles:
    - General Summary
    - Bullet Points
    - Executive Summary
    - Key Takeaways
    - Research Summary
    - Meeting Notes
    - Technical Summary
    - Simple Explanation
    - Action Items

**Example:**
```
https://research-paper.com/study
/Users/you/meeting-recording.mp4
```

### 3. Quick Extract
**Instant extraction directly to clipboard**

- **Usage:** Type "Quick Extract" → Tab → Enter source
- **Input:** Any URL or file path
- **Features:**
  - No UI - works directly from command bar
  - Auto-detects source type
  - Results copied immediately to clipboard
  - Perfect for quick workflows

**Example:**
```
Quick Extract [TAB] https://news.com/article
Quick Extract [TAB] /path/to/document.pdf
```

## Supported Sources

### Web Content
- **Any URL:** Articles, blog posts, documentation
- **Social Media:** Twitter threads, LinkedIn posts
- **News Sites:** Articles and reports
- **Academic:** Research papers and publications

### Documents
- **Text Files:** TXT, MD, RTF
- **Office Documents:** PDF, DOCX, PPTX, XLSX
- **Web Formats:** HTML, XML
- **eBooks:** EPUB

### Media Files
- **Videos:** MP4, AVI, MOV (transcription)
- **Audio:** MP3, WAV, M4A (transcription)  
- **Images:** JPG, PNG, TIFF (OCR)

### Archives
- **Compressed:** ZIP, TAR, GZ
- **Content extraction from archive contents**

## Configuration

### API Keys (Optional but Recommended)

Configure in **Raycast Preferences → Extensions → Content Core**:

#### OpenAI API Key
- **Required for:** Audio/video transcription, AI summarization
- **Get it:** [OpenAI Platform](https://platform.openai.com/api-keys)
- **Format:** `sk-...`

#### Firecrawl API Key  
- **Required for:** Enhanced web scraping (optional)
- **Get it:** [Firecrawl](https://www.firecrawl.dev/)
- **Format:** `fc-...`
- **Benefits:** Better success rate with complex websites

#### Jina AI API Key
- **Required for:** Alternative web scraping service (optional)
- **Get it:** [Jina AI](https://jina.ai/)
- **Format:** `jina_...`
- **Benefits:** Fallback option for web content

### Environment Setup

The extension uses `uvx` for zero-install execution of Content Core:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**No additional setup required** - Content Core is automatically downloaded and cached by `uvx`.

## Features

### Smart Auto-Detection
- **URLs:** Automatically detected and processed as web content
- **File Paths:** Validated for existence and format support
- **Real-time Feedback:** Visual indicators show detected type
- **Error Handling:** Clear messages for invalid inputs

### Rich User Experience
- **Drag & Drop:** Drop files directly onto forms
- **Keyboard Shortcuts:** Full keyboard navigation support
- **Progress Indicators:** Real-time processing status
- **Result Actions:** Copy, paste, save as snippet, create quicklinks

### Output Options
- **Multiple Formats:** Text, JSON, XML for extraction
- **Clipboard Integration:** Direct copy to clipboard
- **Raycast Snippets:** Save results as reusable snippets
- **Quicklinks:** Create shortcuts to original sources

## Keyboard Shortcuts

### Extract Content & Summarize Content
- **⌘ + O:** Choose file browser
- **⌘ + F:** Get Firecrawl API key
- **⌘ + A:** Get OpenAI API key

### Results View
- **⌘ + C:** Copy content to clipboard
- **⌘ + V:** Paste content to active app
- **⌘ + S:** Save as Raycast snippet
- **⌘ + O:** Open original source
- **⌘ + F:** Show in Finder (files only)
- **⌘ + Q:** Create quicklink (summaries only)

## Troubleshooting

### Common Issues

#### "uvx not found"
**Solution:** Install uv package manager
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Then restart Raycast.

#### Web Scraping Failures
**Symptoms:** "Failed to extract content from URL"
**Solutions:**
- Configure Firecrawl API key for better success rates
- Try different URLs or check if site is accessible
- Some sites may block automated access

#### Audio/Video Processing Fails
**Symptoms:** "Transcription failed" or "Media processing error"
**Solutions:**
- Configure OpenAI API key in preferences
- Check file format is supported (MP4, MP3, etc.)
- Verify file is not corrupted and accessible

#### File Access Errors
**Symptoms:** "File not found" or "Permission denied"
**Solutions:**
- Check file path is correct and absolute
- Verify file exists and is readable
- For drag & drop, ensure file isn't moved after dropping

### Performance Tips

#### For Better Speed
- **Smaller files process faster**
- **Local files are faster than URLs**
- **Text formats are faster than media files**

#### For Better Success Rates
- **Use Firecrawl API key for complex websites**
- **Use OpenAI API key for media processing**
- **Try different URLs if extraction fails**

## Examples

### Quick Content Extraction
```
1. Type "Quick Extract"
2. Press Tab
3. Paste: https://blog.example.com/article
4. Press Enter
5. Content copied to clipboard!
```

### Document Summarization
```
1. Type "Summarize Content"  
2. Drag PDF file to form
3. Select "Executive Summary"
4. Click "Generate Summary"
5. Review and copy results
```

### Research Workflow
```
1. "Extract Content" from research paper URL
2. Copy raw content for analysis
3. "Summarize Content" with "Research Summary" style
4. Save summary as Raycast snippet
5. Create quicklink for easy reference
```

## Integration with Content Core

The Raycast extension uses Content Core's powerful processing engine via `uvx`:

- **Zero Install:** No separate Content Core installation needed
- **Always Updated:** Uses latest Content Core version automatically
- **Full Feature Access:** All Content Core capabilities available
- **Shared Configuration:** Uses same API keys as CLI tool

## Feedback and Support

- **Issues:** Report bugs or request features on the [Content Core repository](https://github.com/lfnovo/content-core)
- **Discussions:** Join conversations about use cases and improvements
- **Updates:** Extension updates automatically through Raycast

## Related Integrations

Content Core is also available as:
- **[MCP Server](mcp.md)** - For Claude Desktop integration
- **[macOS Services](macos.md)** - Right-click context menu integration
- **[CLI Tool](../README.md)** - Command line interface

Each integration provides the same powerful content processing with different user experiences optimized for various workflows.