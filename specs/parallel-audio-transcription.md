# Feature: Parallel Audio Transcription

## Feature Description
This feature parallelizes the audio transcription process to improve performance when processing audio files that are split into multiple segments. Currently, audio segments are transcribed sequentially (one after another), which is inefficient. By processing multiple segments concurrently, we can significantly reduce the total transcription time for long audio files.

The feature introduces a configurable concurrency limit (default: 3 concurrent transcriptions) to balance performance with API rate limits and resource usage. Users can customize this limit via an environment variable to match their specific needs and API quotas.

## User Story
As a content extraction user
I want audio files to be transcribed more quickly
So that I can process large audio/video files efficiently without waiting for sequential transcription of each segment

## Problem Statement
Currently, when processing audio files longer than 10 minutes, the system splits them into segments and transcribes each segment serially using a for loop. This is inefficient because:

1. **Wasted API capacity**: Transcription APIs can handle concurrent requests, but we're only using them one at a time
2. **Long processing times**: A 1-hour audio file split into 6 segments takes 6x the time of a single segment instead of roughly the same time with parallelization
3. **Poor user experience**: Users wait unnecessarily for sequential processing when concurrent processing is available
4. **There's already a TODO comment** in the code acknowledging this limitation: `# future: parallelize the transcription process` (line 14 in audio.py)

## Solution Statement
Implement concurrent transcription using `asyncio.gather()` with a configurable semaphore to limit concurrent requests. This approach:

1. **Processes multiple segments simultaneously**: Uses asyncio's natural concurrency to transcribe multiple segments at once
2. **Configurable concurrency limit**: Defaults to 3 concurrent requests, customizable via `CCORE_AUDIO_CONCURRENCY` environment variable
3. **Maintains order**: Results are collected in the correct order despite concurrent processing
4. **Respects rate limits**: The semaphore prevents overwhelming the API with too many concurrent requests
5. **Follows existing patterns**: Uses the same configuration approach as other features (environment variables + YAML config)

## Relevant Files
Use these files to implement the feature:

- **src/content_core/processors/audio.py** (lines 101-159)
  - Contains `transcribe_audio_segment()` function (line 101-103) - already async, ready for parallelization
  - Contains `extract_audio_data()` function (lines 106-159) - where the serial loop needs to be replaced with concurrent processing
  - Lines 140-149 contain the serial transcription loop that needs to be parallelized

- **src/content_core/config.py**
  - Configuration module that handles environment variables and YAML config loading
  - Contains functions like `get_document_engine()` and `get_url_engine()` that demonstrate the pattern for environment variable overrides
  - Need to add `get_audio_concurrency()` function following the same pattern

- **src/content_core/cc_config.yaml**
  - Main configuration file with extraction settings
  - Need to add `audio.concurrency` configuration option under the `extraction` section

- **tests/unit/test_file_detector_performance.py**
  - Example of existing test file structure (though not audio-specific)
  - Reference for understanding the test organization pattern

- **README.md** (lines 285-314)
  - Documents configuration options including environment variables
  - Need to document the new `CCORE_AUDIO_CONCURRENCY` environment variable

### New Files

- **tests/unit/test_audio_concurrency.py**
  - Unit tests for the parallel transcription functionality
  - Tests for semaphore limiting
  - Tests for configuration loading
  - Mock-based tests to avoid actual API calls

## Implementation Plan

### Phase 1: Foundation
Add the configuration infrastructure to support the new concurrency setting. This includes updating the YAML config file, adding environment variable support, and creating getter functions following existing patterns.

### Phase 2: Core Implementation
Implement the parallel transcription logic using `asyncio.gather()` with a semaphore for concurrency limiting. Replace the serial for loop with concurrent task execution while maintaining result ordering.

### Phase 3: Integration
Update documentation, add comprehensive tests, and validate the feature works end-to-end without breaking existing functionality.

## Step by Step Tasks

### 1. Update Configuration Files
- Add `audio.concurrency` setting to `cc_config.yaml` under the `extraction` section with default value of 3
- Add validation for the concurrency value (must be positive integer)

### 2. Add Configuration Helper Functions
- Add `get_audio_concurrency()` function to `config.py` following the pattern of `get_document_engine()` and `get_url_engine()`
- Support `CCORE_AUDIO_CONCURRENCY` environment variable override
- Add validation to ensure the value is a positive integer (1-10 range recommended)
- Add warning logging for invalid values with fallback to default

### 3. Implement Parallel Transcription Logic
- Refactor `extract_audio_data()` in `audio.py` to use `asyncio.gather()` instead of the serial for loop
- Create a semaphore using `asyncio.Semaphore(get_audio_concurrency())` to limit concurrent transcriptions
- Wrap `transcribe_audio_segment()` calls with semaphore context manager
- Ensure transcription results maintain correct order despite concurrent processing
- Keep existing error handling and logging behavior

### 4. Create Unit Tests
- Create `tests/unit/test_audio_concurrency.py` with mock-based tests
- Test: Default concurrency value (3) is used when no config provided
- Test: Environment variable override works correctly
- Test: YAML config value is respected
- Test: Invalid concurrency values fall back to default with warning
- Test: Semaphore correctly limits concurrent executions
- Test: Results maintain correct order after parallel processing
- Use `unittest.mock` to mock the speech-to-text model and avoid actual API calls

### 5. Create Integration Test
- Add test case to `tests/integration/test_extraction.py` (if it doesn't exist, create it)
- Test: Audio file processing with multiple segments completes successfully
- Test: Verify transcription results are concatenated in correct order
- Use a small test audio file that can be split into 2-3 segments for testing

### 6. Update Documentation
- Update `README.md` section on environment variables (around line 510) to document `CCORE_AUDIO_CONCURRENCY`
- Add entry in the "Configuration" section explaining the new setting
- Include example `.env` snippet showing the new variable
- Document recommended range (1-10) and default value (3)

### 7. Remove TODO Comment
- Remove or update the TODO comment on line 14 of `audio.py`: `# future: parallelize the transcription process`
- Update to acknowledge the feature is now implemented

### 8. Run Validation Commands
- Execute all validation commands listed below to ensure zero regressions
- Fix any issues discovered during validation
- Verify performance improvement with timing logs

## Testing Strategy

### Unit Tests
- **Configuration Loading**: Test `get_audio_concurrency()` with various inputs (env var, YAML, defaults, invalid values)
- **Semaphore Behavior**: Mock transcription function to verify only N tasks run concurrently at any time
- **Result Ordering**: Verify transcription results are concatenated in the correct order despite concurrent execution
- **Error Handling**: Verify errors in one segment don't prevent other segments from processing

### Integration Tests
- **End-to-End Processing**: Process a real (small) audio file split into multiple segments
- **Concurrency Verification**: Add timing logs to verify parallel execution is actually faster
- **API Integration**: Verify the feature works with actual OpenAI Whisper API (in integration test only, not unit test)

### Edge Cases
- **Single segment audio**: Audio shorter than 10 minutes should still work (no parallelization needed)
- **Concurrency of 1**: Setting concurrency to 1 should behave like serial processing
- **Invalid concurrency values**: Zero, negative, non-integer, or excessive values should fall back to default
- **Empty audio file list**: Handle gracefully without errors
- **Transcription failures**: One failed segment shouldn't break the entire process

## Acceptance Criteria
- Audio segments are transcribed concurrently with configurable concurrency limit
- Default concurrency is 3 concurrent transcriptions
- `CCORE_AUDIO_CONCURRENCY` environment variable can override the default
- Configuration can be set in `cc_config.yaml` under `extraction.audio.concurrency`
- Invalid configuration values log warnings and fall back to default (3)
- Transcription results maintain correct sequential order despite parallel processing
- All existing tests pass without modifications
- New unit tests cover configuration, semaphore behavior, and result ordering
- Documentation is updated to explain the new configuration option
- Performance improvement is measurable (timing logs show reduced processing time for multi-segment files)
- No breaking changes to existing audio processing functionality

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

- `make test` - Run all tests to validate the feature works with zero regressions
- `uv run pytest tests/unit/test_audio_concurrency.py -v` - Run new audio concurrency unit tests
- `uv run pytest tests/integration/test_extraction.py -v -k audio` - Run audio-related integration tests
- `make ruff` - Ensure code formatting and linting passes
- `uv run python -c "from content_core.config import get_audio_concurrency; print(f'Default concurrency: {get_audio_concurrency()}')"` - Verify config function works
- `CCORE_AUDIO_CONCURRENCY=5 uv run python -c "from content_core.config import get_audio_concurrency; print(f'Override concurrency: {get_audio_concurrency()}')"` - Verify environment variable override
- `uvx --from "content-core" ccore tests/input_content/file_audio.mp3` - End-to-end test with CLI (if audio file exists)

## Clarification Needed
None. The requirements are clear:
- Parallelize audio transcription using asyncio.gather()
- Default concurrency of 3
- Configurable via `CCORE_AUDIO_CONCURRENCY` environment variable
- Follow existing configuration patterns in the codebase

## Notes

### Performance Considerations
- **API Rate Limits**: Default of 3 concurrent requests is conservative to avoid hitting rate limits. Users with higher quotas can increase this.
- **Memory Usage**: Concurrent processing will hold more audio segments in memory. This is acceptable for the default segment size (10 minutes).
- **Network I/O**: Transcription is network I/O bound, making it ideal for async concurrency.

### Implementation Notes
- The `transcribe_audio_segment()` function is already async (line 101-103), making it ready for concurrent execution
- Use `asyncio.Semaphore` for limiting concurrency, not thread pools, since the work is I/O bound
- Maintain the existing error handling pattern with try/except blocks and logging

### Future Enhancements (Out of Scope)
- Dynamic concurrency adjustment based on API response times
- Per-provider concurrency limits (e.g., different limits for OpenAI vs Google)
- Progress tracking for multi-segment transcriptions
- Retry logic for failed segments

### Configuration Pattern
This feature follows the established configuration pattern seen in:
- `get_document_engine()` - environment variable override with validation
- `get_url_engine()` - YAML config with fallback to defaults
- `set_pymupdf_ocr_enabled()` - programmatic configuration override

### Dependencies
No new dependencies required. Uses existing:
- `asyncio` - part of Python standard library
- `esperanto` - already used for AI model management
- `loguru` - already used for logging
