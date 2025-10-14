# OSS-208: Add MCP Summarize Tool for Extract+Summarize Workflows

## Context (WHY)

### Problem Statement
MCP/LLM developers using Claude Desktop need efficient content processing workflows. Currently, they must:
1. First extract content using `extract_content` tool
2. Then separately summarize it in another step
3. This creates workflow friction and context switching

### Business Value
- **Workflow Efficiency**: Reduce steps from 2 to 1 for common extract+summarize operations
- **Superior Quality**: Leverage Content Core's specialized engines (Docling, Firecrawl, Whisper) for better extraction quality before summarization
- **Guided Experience**: Pre-defined prompts help users discover effective summarization patterns
- **Professional Output**: Consistent, high-quality summaries for different use cases

## Goal (WHAT)

### Core Deliverables

1. **MCP Tool: `summarize_content`**
   - Combines extraction and summarization in a single operation
   - Parameters:
     - `source` (required): URL or file path
     - `style` (optional): Pre-defined style [`bullet_points`, `executive_summary`, `technical_overview`, `action_items`]
     - `custom_context` (optional): Custom summarization instructions
   - Returns: Plain text summary string
   - Throws exceptions for errors (MCP framework handles error responses)
   - **Flexibility**: When `custom_context` is provided, it takes precedence over `style`, allowing users to bypass the 4 pre-defined styles entirely

2. **Four MCP Prompts**
   - `summarize_bullet_points`: Extract key information as scannable bullet points
   - `create_executive_summary`: Generate high-level overview for leadership
   - `generate_technical_overview`: Provide detailed technical analysis
   - `extract_action_items`: Identify actionable tasks and next steps

### Success Criteria
- All 4 predefined prompts working in Claude Desktop
- Tool handles all supported Content Core file types
- Error handling provides clear, actionable messages via exceptions
- Performance: <10s response time for documents <10MB
- Zero regressions in existing MCP functionality

## Approach (HOW)

### Implementation Strategy

1. **Extend Existing MCP Server**
   - Add new tool to `src/content_core/mcp/server.py`
   - Leverage existing `_extract_content_impl()` for extraction
   - Use existing `summarize()` from `content_core.content.summary`

2. **Jinja Templates for Styles**
   - Create prompt templates in `prompts/mcp/` directory:
     - `bullet_points.jinja`
     - `executive_summary.jinja`
     - `technical_overview.jinja`
     - `action_items.jinja`
   - Templates allow for future customization and maintainability
   - **Priority**: `custom_context` > `style` > default context
   - Users can completely ignore pre-defined styles by providing `custom_context`

3. **Prompts as Tool Wrappers**
   - Implement each prompt as `@mcp.prompt` decorator function
   - Prompts call `summarize_content` tool internally
   - Handle optional arguments by concatenating to context

4. **Error Handling**
   - Throw appropriate exceptions (ValueError, FileNotFoundError, etc.)
   - Let MCP framework convert exceptions to error responses
   - Include descriptive error messages for debugging

## Testing Strategy

### Unit Tests Only (Initial Phase)
- Test `summarize_content` tool with various inputs:
  - Valid URLs and file paths
  - Different style options
  - Custom context handling
  - Error cases (invalid source, network errors)
- Test each prompt function:
  - Argument handling
  - Context concatenation
  - Tool invocation

### Files to Test
- `tests/test_mcp_summarize.py` - New test file for summarize functionality
- Existing `tests/test_mcp_server.py` - Ensure no regressions

## Dependencies

### External
- No new external dependencies required

### Internal  
- `content_core.content.extraction.extract_content` - For content extraction
- `content_core.content.summary.summarize` - For AI summarization
- `fastmcp` - MCP framework (already in use)
- `ai_prompter` - For Jinja template rendering

## Constraints

### Technical
- Must maintain backward compatibility with existing MCP server
- Memory usage constraints for large document processing
- AI provider rate limits and quota management
- Must work with all existing Content Core extraction engines

### Business
- Open source implementation
- Must complete within current sprint
- Documentation updates required for MCP docs

## Assumptions

1. Users have AI provider credentials configured (OpenAI, Anthropic, etc.)
2. Content Core extraction engines handle user's typical file types
3. Claude Desktop MCP integration remains stable
4. Jinja templates are acceptable for prompt contexts (confirmed by user)
5. Exception-based error handling is preferred (confirmed by user)

## Open Questions
None - all clarifications have been addressed.

## Implementation Checklist

- [ ] Create Jinja templates for 4 summarization styles
- [ ] Implement `summarize_content` tool in MCP server
- [ ] Implement 4 MCP prompts
- [ ] Write comprehensive unit tests
- [ ] Update MCP documentation
- [ ] Test with Claude Desktop
- [ ] Ensure no regressions in existing functionality