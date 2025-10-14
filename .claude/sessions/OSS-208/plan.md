# OSS-208: Add MCP Summarize Tool Implementation Plan

If you are working on this feature, make sure to update this plan.md file as you go.

## PHASE 1: Create Jinja Templates [Not Started ⏳]

Create the four summarization style templates that will power the pre-defined prompts. These templates need to be created first as they are dependencies for both the tool and prompt implementations.

### Create prompts/mcp directory structure [Not Started ⏳]

- Create the `prompts/mcp/` directory
- Ensure proper file permissions and structure

### Create bullet_points.jinja template [Not Started ⏳]

- Template should instruct AI to create scannable bullet points
- Focus on key facts, insights, and takeaways
- Support optional `additional_context` variable

### Create executive_summary.jinja template [Not Started ⏳]

- Template for high-level overview suitable for leadership
- Focus on business implications and strategic takeaways
- Support optional `target_audience` variable

### Create technical_overview.jinja template [Not Started ⏳]

- Template for detailed technical analysis
- Include methodology, implementation details, technical insights
- Support optional `focus_area` variable

### Create action_items.jinja template [Not Started ⏳]

- Template to extract specific tasks and next steps
- Include deadlines, responsible parties, dependencies
- Support optional `deadline_context` variable

### Comments:
- Templates should be concise but clear in their instructions
- Each template should handle the case where additional context is not provided
- Templates will use the same pattern as existing content/summarize.jinja

## PHASE 2: Implement Core Tool [Not Started ⏳]

Implement the `summarize_content` tool in the MCP server that combines extraction and summarization.

### Add summarize_content tool to server.py [Not Started ⏳]

- Implement the main tool function with proper FastMCP decorator
- Add input validation for source parameter
- Implement source type detection (URL vs file path)

### Implement extraction logic [Not Started ⏳]

- Use existing `_extract_content_impl()` for extraction
- Handle both URL and file path sources
- Proper error handling for extraction failures

### Implement context determination logic [Not Started ⏳]

- Priority: custom_context > style > default
- Load and render Jinja templates for style-based contexts
- Use ai_prompter.Prompter for template rendering

### Implement summarization call [Not Started ⏳]

- Call existing `summarize()` function with extracted content and context
- Handle AI provider errors appropriately
- Return summary as plain text string

### Comments:
- Must maintain compatibility with existing extract_content tool
- Error handling via exceptions (not structured returns)
- Need to handle large files gracefully

## PHASE 3: Implement MCP Prompts [Not Started ⏳]

Create the four MCP prompts that act as convenient wrappers around the summarize_content tool.

### Implement summarize_bullet_points prompt [Not Started ⏳]

- Create `@mcp.prompt` decorated function
- Accept source and additional_context parameters
- Call summarize_content with appropriate custom_context

### Implement create_executive_summary prompt [Not Started ⏳]

- Create `@mcp.prompt` decorated function
- Accept source and target_audience parameters
- Format context string appropriately

### Implement generate_technical_overview prompt [Not Started ⏳]

- Create `@mcp.prompt` decorated function
- Accept source and focus_area parameters
- Concatenate focus_area to base context if provided

### Implement extract_action_items prompt [Not Started ⏳]

- Create `@mcp.prompt` decorated function
- Accept source and deadline_context parameters
- Build appropriate context string

### Comments:
- Prompts should be thin wrappers, minimal logic
- All prompts call summarize_content with custom_context
- Parameter names must match the spec exactly

## PHASE 4: Testing Implementation [Not Started ⏳]

Create comprehensive unit tests for the new functionality.

### Create test_mcp_summarize.py file [Not Started ⏳]

- Set up test class structure
- Import necessary testing utilities and mocks
- Configure test fixtures

### Implement tool tests [Not Started ⏳]

- Test with valid URL input
- Test with valid file path input
- Test with each style option
- Test custom_context override behavior
- Test error cases (invalid source, missing file, network errors)

### Implement prompt tests [Not Started ⏳]

- Test each of the 4 prompts
- Test optional parameter handling
- Test that prompts correctly call summarize_content
- Verify context string formation

### Run regression tests [Not Started ⏳]

- Run existing test_mcp_server.py tests
- Ensure extract_content still works
- Verify no memory leaks or performance issues

### Comments:
- Use mocking for AI calls to avoid API costs during testing
- Tests should be fast and deterministic
- Cover edge cases like empty content, very large files

## PHASE 5: Documentation and Manual Testing [Not Started ⏳]

Update documentation and perform manual testing with Claude Desktop.

### Update docs/mcp.md documentation [Not Started ⏳]

- Document new summarize_content tool
- Document all 4 prompts with examples
- Add usage examples and best practices
- Include error handling guidance

### Manual testing with Claude Desktop [Not Started ⏳]

- Test tool discovery in Claude Desktop
- Verify all 4 prompts appear in prompt list
- Test with real files and URLs
- Verify error messages are helpful

### Create example usage scripts [Not Started ⏳]

- Create examples/ directory if needed
- Add example script showing tool usage
- Add example showing prompt usage
- Include common use cases

### Comments:
- Documentation should include both basic and advanced usage
- Manual testing critical for user experience validation
- Examples help users understand the feature quickly

## PHASE 6: Final Review and Cleanup [Not Started ⏳]

Final checks and preparation for merge.

### Code review and cleanup [Not Started ⏳]

- Remove any debug print statements
- Ensure consistent code style (ruff)
- Add appropriate type hints
- Review error messages for clarity

### Performance validation [Not Started ⏳]

- Test with large documents (<10MB)
- Verify response time <10s requirement
- Check memory usage during processing
- Test concurrent requests if applicable

### Update Linear ticket [Not Started ⏳]

- Update ticket status
- Add implementation notes
- Document any deviations from spec
- Note any follow-up items

### Comments:
- This phase ensures production readiness
- Performance testing critical for user satisfaction
- Linear update keeps stakeholders informed

## Dependencies and Parallelization Notes

**Sequential Requirements:**
1. Phase 1 (Templates) must complete before Phase 2 (Tool)
2. Phase 2 (Tool) must complete before Phase 3 (Prompts)
3. Phase 4 (Testing) can start partially with Phase 2, but needs Phase 3 for prompt tests
4. Phase 5 (Documentation) can start anytime but needs all code complete for examples
5. Phase 6 (Review) must be last

**Parallel Opportunities:**
- Within Phase 1: All templates can be created in parallel
- Within Phase 3: All prompts can be implemented in parallel
- Phase 5 documentation writing can begin early (while coding)

## Risk Mitigation

**Key Risks:**
1. **Template Loading**: Ensure ai_prompter can find MCP templates
2. **Error Propagation**: Verify FastMCP properly converts exceptions
3. **Memory Issues**: Large file handling needs careful testing
4. **AI Rate Limits**: Tests should mock AI calls to avoid limits

**Mitigation Strategies:**
- Test template loading early in Phase 2
- Create simple error test first to verify exception handling
- Use test files of various sizes in Phase 4
- Mock all AI calls in unit tests

## Success Criteria Checklist

- [ ] All 4 Jinja templates created and valid
- [ ] summarize_content tool working with URLs
- [ ] summarize_content tool working with files
- [ ] All 4 prompts discoverable in Claude Desktop
- [ ] Custom context overrides style correctly
- [ ] All unit tests passing
- [ ] No regression in existing functionality
- [ ] Documentation complete and clear
- [ ] Performance <10s for typical documents
- [ ] Error messages helpful and actionable