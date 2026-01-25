# Common Module

Shared infrastructure for content-core: exceptions, retry logic, state management, and utilities.

## Files

- **`exceptions.py`**: Exception hierarchy with `ContentCoreError` as base. Key exceptions: `UnsupportedTypeException`, `InvalidInputError`, `NotFoundError`, `NoTranscriptFound`, `NetworkError`
- **`retry.py`**: Tenacity-based retry decorators for transient failures. Uses `get_retry_config()` from config. Exports: `retry_youtube`, `retry_url_api`, `retry_url_network`, `retry_audio_transcription`, `retry_llm`, `retry_download`
- **`state.py`**: Pydantic models for LangGraph workflow state. `ProcessSourceInput` (API input), `ProcessSourceState` (internal state), `ProcessSourceOutput` (API output)
- **`types.py`**: Type aliases for engine selection: `DocumentEngine`, `UrlEngine`
- **`utils.py`**: Helper `process_input_content()` to detect and extract from URLs/files

## Patterns

- **Exception handling**: All custom exceptions inherit from `ContentCoreError`. Use specific exceptions like `UnsupportedTypeException` for type mismatches
- **Retry decorators**: Applied as function decorators, not class methods. They read config via `get_retry_config(operation_type)`. Non-retryable exceptions (e.g., `NotFoundError`, `NoTranscriptFound`) bypass retry
- **State flow**: `ProcessSourceInput` -> `ProcessSourceState` (internal) -> `ProcessSourceOutput`. State models use optional fields with defaults

## Integration

- Imported by: All processors, extraction graph, tools, templated_message
- Imports from: `content_core.config`, `content_core.logging`
- `retry.py` depends on `config.get_retry_config()` for retry parameters

## Gotchas

- Retry decorators must wrap internal functions (prefixed with `_`), not the public API functions
- `NON_RETRYABLE_EXCEPTIONS` in retry.py determines which errors skip retry - add new permanent failure types there
- `ProcessSourceState` has more fields than `ProcessSourceInput` - it accumulates data during workflow execution
- `process_input_content()` uses validators library for URL detection, regex for file paths

## When Adding Code

- New exceptions must inherit from `ContentCoreError`
- New retry decorators should follow the pattern: config lookup, tenacity decorator, before_sleep logging
- State fields should be Optional with defaults to support partial workflow execution
