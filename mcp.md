# MCP Server Implementation Plan for Content Core

## Overview
Implement a FastMCP server that exposes Content Core's extraction functionality through the Model Context Protocol (MCP). The server will provide a single tool `extract_content` that accepts either a URL or file path and returns extracted content in JSON format using the 'auto' engine.

## Architecture

### 1. Dependencies
```toml
# Add to pyproject.toml as optional dependency
[project.optional-dependencies]
mcp = ["fastmcp>=0.5.0"]

# Add script entry point for uvx
[project.scripts]
content-core-mcp = "content_core.mcp.server:main"
```

This allows users to install with MCP support using:
```bash
pip install content-core[mcp]
# or with uv
uv pip install content-core[mcp]
```

### 2. Server Structure
```
src/content_core/
├── mcp/
│   ├── __init__.py
│   └── server.py       # Main MCP server implementation
```

### 3. Implementation Details

#### Server Setup (`server.py`)
```python
from fastmcp import FastMCP
from typing import Optional, Dict, Any
import content_core as cc

# Initialize MCP server
mcp = FastMCP("Content Core MCP Server")
```

#### Tool Definition
The `extract_content` tool will:
- Accept either `url` or `file_path` as optional parameters
- Validate that exactly one is provided
- Return extracted content in JSON format
- Use the 'auto' engine by default

```python
@mcp.tool
async def extract_content(
    url: Optional[str] = None,
    file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract content from a URL or file using Content Core's auto engine.
    
    Args:
        url: Optional URL to extract content from
        file_path: Optional file path to extract content from
        
    Returns:
        JSON object containing extracted content and metadata
        
    Raises:
        ValueError: If neither or both url and file_path are provided
    """
    # Implementation details below
```

#### Input Validation
- Ensure exactly one input source is provided
- Validate URL format if URL is provided
- Validate file existence if file_path is provided

#### Integration with Content Core
```python
# Build extraction request
extraction_request = {}
if url:
    extraction_request["url"] = url
elif file_path:
    extraction_request["file_path"] = file_path

# Use Content Core's extract_content with auto engine
result = await cc.extract_content(extraction_request)
```

#### Return Format
The tool will return a JSON structure containing:
```json
{
    "source_type": "url" | "file",
    "source": "<url or file_path>",
    "content": "<extracted content>",
    "metadata": {
        "engine_used": "<actual engine used by auto>",
        "content_type": "<detected content type>",
        "extraction_time": "<ISO timestamp>",
        // Additional metadata from Content Core
    },
    "success": true,
    "error": null  // or error message if extraction failed
}
```

#### Error Handling
- Wrap extraction in try/except block
- Return structured error response on failure
- Log errors using Context if needed
- Handle specific Content Core exceptions

### 4. Running the Server

#### Entry Point (`main` function)
```python
def main():
    """Entry point for the MCP server."""
    import sys
    # Run with STDIO transport for MCP compatibility
    mcp.run()

if __name__ == "__main__":
    main()
```

#### Usage with uvx
Users can run the server directly with uvx (no installation required):
```bash
# Run the MCP server
uvx --from "content-core[mcp]" content-core-mcp
```

#### Claude Desktop Configuration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "content-core": {
      "command": "uvx",
      "args": [
        "--from",
        "content-core[mcp]",
        "content-core-mcp"
      ]
    }
  }
}
```

#### Alternative: Local Development
```bash
# Install with MCP support
uv pip install -e ".[mcp]"

# Run directly
content-core-mcp
```

### 5. Testing Strategy

#### Unit Tests
- Test input validation logic
- Mock Content Core extraction calls
- Verify JSON response structure

#### Integration Tests
- Test with real URLs
- Test with various file types
- Verify auto engine selection works correctly

### 6. Documentation

#### Usage Example
```python
# Client code example
from fastmcp import Client

client = Client()
result = await client.call_tool(
    "extract_content",
    {"url": "https://example.com/article"}
)
```

### 7. Configuration

#### Environment Variables
- Support existing Content Core environment variables
- Allow MCP-specific configuration if needed

#### Config File Support
- Use existing `cc_config.yaml` if present
- Allow override via MCP server initialization

### 8. Future Enhancements (Not in initial implementation)
- Add streaming support for large files
- Support for multiple URLs/files in one request
- Add content cleaning and summarization tools
- Support custom extraction engines per request
- Add resource endpoints for browsing extracted content

### 9. Implementation Steps

1. Create `mcp/` directory structure
2. Implement basic server with extract_content tool
3. Add input validation and error handling
4. Integrate with Content Core extraction
5. Format JSON response properly
6. Add comprehensive logging
7. Write unit tests
8. Write integration tests
9. Add documentation and examples
10. Test with various MCP clients

### 10. Key Considerations

- **Async First**: Use async/await throughout since Content Core is async
- **Error Messages**: Provide clear, actionable error messages
- **Performance**: Consider caching for repeated requests
- **Security**: Validate file paths to prevent directory traversal
- **Compatibility**: Ensure works with all Content Core extraction engines

### 11. Publishing and Distribution

#### PyPI Package
The MCP server will be included as an optional extra in the main content-core package:
- Users install with `pip install content-core[mcp]`
- The `content-core-mcp` command becomes available after installation
- Works seamlessly with `uvx` for zero-install usage

#### Benefits of uvx approach:
1. **No installation required**: Users can run directly with `uvx`
2. **Automatic updates**: Always uses the latest published version
3. **Isolation**: Runs in isolated environment, avoiding dependency conflicts
4. **Simple configuration**: Just add to `claude_desktop_config.json`

#### Example MCP server listing entry:
```yaml
name: content-core
description: Extract content from URLs and files using Content Core
commands:
  - uvx --from "content-core[mcp]" content-core-mcp
```