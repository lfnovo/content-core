# Tools Module

LangChain tool wrappers for content-core operations. Provides `@tool` decorated functions for agent integration.

## Files

- **`extract.py`**: `extract_content_tool` - extracts content from URLs or file paths
- **`cleanup.py`**: `cleanup_content_tool` - cleans and rewrites content with LLM
- **`summarize.py`**: `summarize_content_tool` - summarizes content with optional context

## Patterns

- **Tool decorator**: All functions use `@tool` from `langchain_core.tools`
- **Input preprocessing**: Tools call `process_input_content()` to handle URL/file path inputs before processing
- **Async**: All tool functions are async

## Integration

- Imports from: `content_core.extraction`, `content_core.content_cleanup`, `content_core.content_summary`, `content_core.common`
- Used by: External agents using LangChain/LangGraph

## Gotchas

- Tools auto-extract content from URLs/files via `process_input_content()` before processing
- Import paths use aliases: `content_core.extraction` (not `content_core.content.extraction`)

## When Adding Code

- New tools must use `@tool` decorator and be async
- Add new tools to `__init__.py` exports
- Use `process_input_content()` if the tool should accept URLs/file paths as input
