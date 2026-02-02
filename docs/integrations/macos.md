# macOS Services Integration

Content Core can be integrated into macOS Finder as right-click context menu services, allowing you to extract and summarize content directly from files without any installation.

## Features

- **Right-click integration**: Extract or summarize any file directly from Finder
- **Zero-install processing**: Uses `uvx` for isolated execution
- **Multiple output options**: Clipboard or TextEdit display
- **System notifications**: Get notified when processing completes
- **Wide format support**: PDFs, Word docs, videos, audio files, images, and more

## Quick Setup

### Prerequisites

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Restart your terminal** after installation

### Create the Services

We'll create **4 different services** for different use cases:

1. **Extract Content → Clipboard**
2. **Extract Content → TextEdit**  
3. **Summarize Content → Clipboard**
4. **Summarize Content → TextEdit**

## Service Scripts

### 1. Extract Content → Clipboard

**Service Name:** `Extract Content (Clipboard)`

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

for file in "$@"; do
    echo "Extracting content from: $(basename "$file")"
    uvx --from "content-core" ccore "$file" | pbcopy
    osascript -e 'display notification "Content extracted and copied to clipboard" with title "Content Core"'
done
```

### 2. Extract Content → TextEdit

**Service Name:** `Extract Content (TextEdit)`

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

for file in "$@"; do
    filename=$(basename "$file")
    echo "Extracting content from: $filename"
    
    # Create temporary file for the extracted content
    temp_file="/tmp/extracted_$(date +%s)_$filename.txt"
    
    # Extract content and save to temp file
    uvx --from "content-core" ccore "$file" > "$temp_file"
    
    # Open in TextEdit
    open -a "TextEdit" "$temp_file"
    
    osascript -e 'display notification "Content extracted and opened in TextEdit" with title "Content Core"'
done
```

### 3. Summarize Content → Clipboard

**Service Name:** `Summarize Content (Clipboard)`

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

for file in "$@"; do
    echo "Summarizing content from: $(basename "$file")"
    uvx --from "content-core" csum "$file" 2>/dev/null | pbcopy
    osascript -e 'display notification "Summary copied to clipboard" with title "Content Core"'
done
```

### 4. Summarize Content → TextEdit

**Service Name:** `Summarize Content (TextEdit)`

```bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

for file in "$@"; do
    filename=$(basename "$file")
    echo "Summarizing content from: $filename"
    
    # Create temporary file for the summary
    temp_file="/tmp/summary_$(date +%s)_$filename.txt"
    
    # Add header to the summary
    echo "=== SUMMARY OF: $filename ===" > "$temp_file"
    echo "Generated on: $(date)" >> "$temp_file"
    echo "" >> "$temp_file"
    
    # Generate summary and append to temp file
    uvx --from "content-core" csum "$file" 2>/dev/null >> "$temp_file"
    
    # Open in TextEdit
    open -a "TextEdit" "$temp_file"
    
    osascript -e 'display notification "Summary opened in TextEdit" with title "Content Core"'
done
```

## Step-by-Step Installation

### For Each Service:

1. **Open Automator** (Cmd+Space → type "Automator")
2. Choose **"Quick Action"**
3. Configure the service:
   - Set **"Workflow receives current"** → **"files or folders"**
   - Set **"in"** → **"Finder"**
4. **Drag "Run Shell Script"** from Actions to the workflow area
5. **Configure the shell script**:
   - Make sure **"Pass input: as arguments"** is selected
   - **Paste the appropriate script** from above
6. **Save** with the service name (e.g., "Extract Content (Clipboard)")
7. **Repeat** for all 4 services

## Usage

After installation, **right-click any supported file** in Finder:

### In the Services submenu, you'll see:
- **Extract Content (Clipboard)** - Content copied to clipboard
- **Extract Content (TextEdit)** - Content opens in TextEdit  
- **Summarize Content (Clipboard)** - Summary copied to clipboard
- **Summarize Content (TextEdit)** - Summary opens in TextEdit

### Supported File Types

Content Core services work with:

#### Documents
- **PDFs** - Text extraction with layout preservation
- **Word Documents** (.docx) - Full text and formatting
- **PowerPoint** (.pptx) - Slide content and speaker notes
- **Excel** (.xlsx) - Cell data and formulas
- **Text files** (.txt, .md, .csv)

#### Web & Markup
- **HTML files** - Clean text extraction
- **Markdown files** - Formatted content
- **EPUB books** - Chapter text

#### Media Files
- **Videos** (.mp4, .avi, .mov, .mkv) - Automatic transcription
- **Audio** (.mp3, .wav, .m4a, .flac) - Speech-to-text conversion
- **Images** (.jpg, .png, .tiff) - OCR text extraction

#### Archives
- **ZIP files** - Extract text from contained files
- **Compressed formats** - Automatic extraction and processing

## Customization

### Custom Output Locations

Want to save to a specific folder instead of temp files? Modify the TextEdit scripts:

```bash
# Save to Desktop
output_file="~/Desktop/extracted_$filename.txt"

# Save to Documents folder
output_file="~/Documents/ContentCore/extracted_$filename.txt"
```

### Custom Summary Context

Add context to your summaries by modifying the csum command:

```bash
# Summarize as bullet points
uvx --from "content-core" csum "$file" --context "bullet points"

# Summarize for a specific audience
uvx --from "content-core" csum "$file" --context "explain to a child"

# Executive summary
uvx --from "content-core" csum "$file" --context "executive summary"
```

### JSON Output

For structured data, use JSON format:

```bash
uvx --from "content-core" ccore "$file" --format json
```

## Troubleshooting

### Services Not Appearing?

1. **Restart Finder**: `killall Finder`
2. **Check Services settings**:
   - Go to **System Preferences** → **Keyboard** → **Shortcuts** → **Services**
   - Look in **"Files and Folders"** section
   - **Enable** the Content Core services

### Permission Issues?

- macOS might ask for permission to run scripts
- **Grant access** when prompted
- Check **Security & Privacy** settings if needed

### uvx Not Found Error?

- Make sure the **PATH export line** is at the top of each script
- Verify uvx location: `which uvx`
- Update the PATH if uvx is in a different location

### Services Work But No Content?

- Check if you have the required API keys for certain content types:
  - **OPENAI_API_KEY** - Required for audio/video transcription
  - **FIRECRAWL_API_KEY** - Optional, for better web content extraction

Add API keys to your shell profile:
```bash
echo 'export OPENAI_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

## Advanced Usage

### Keyboard Shortcuts

Assign keyboard shortcuts to your services:

1. **System Preferences** → **Keyboard** → **Shortcuts** → **Services**
2. Find your Content Core services
3. **Click** next to the service name
4. **Press** your desired key combination

### Batch Processing

Services work with **multiple selected files**:

1. **Select multiple files** in Finder (Cmd+click)
2. **Right-click** → **Services** → Choose your service
3. **All files** will be processed sequentially

### Integration with Other Apps

The extracted content works great with:

- **Note-taking apps** (Obsidian, Notion, Bear)
- **Research tools** (DEVONthink, Zotero)
- **Writing apps** (Ulysses, Scrivener)
- **Code editors** (VS Code, Sublime Text)

Simply use the clipboard versions and paste into your preferred app!

## Tips & Best Practices

1. **Use descriptive file names** - They appear in notifications
2. **Process one large file at a time** - Videos/audio take time to transcribe
3. **Check clipboard** after extraction - Some content might be very long
4. **Use TextEdit version** for long documents to review before copying
5. **Set up API keys** for full functionality with media files

## Uninstalling

To remove the services:

```bash
rm -rf ~/Library/Services/"Extract Content (Clipboard).workflow"
rm -rf ~/Library/Services/"Extract Content (TextEdit).workflow"  
rm -rf ~/Library/Services/"Summarize Content (Clipboard).workflow"
rm -rf ~/Library/Services/"Summarize Content (TextEdit).workflow"
```

Then restart Finder: `killall Finder`