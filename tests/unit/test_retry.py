"""
Unit tests for retry decorators and configuration.

Tests the retry module including:
- Configuration loading and environment variable overrides
- Decorator behavior (retries, backoff, logging)
- Exception handling after retry exhaustion
"""
import os
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from content_core.common.exceptions import NoTranscriptFound, NotFoundError
from content_core.common.retry import (
    is_retryable_exception,
    log_retry_attempt,
    retry_audio_transcription,
    retry_download,
    retry_llm,
    retry_url_api,
    retry_url_network,
    retry_youtube,
)
from content_core.config import (
    DEFAULT_RETRY_CONFIG,
    get_retry_config,
)


class TestRetryConfig:
    """Tests for retry configuration loading."""

    def test_default_config_values(self):
        """Test that default configuration values are correct."""
        assert DEFAULT_RETRY_CONFIG["youtube"] == {
            "max_attempts": 5,
            "base_delay": 2,
            "max_delay": 60,
        }
        assert DEFAULT_RETRY_CONFIG["url_api"] == {
            "max_attempts": 3,
            "base_delay": 1,
            "max_delay": 30,
        }
        assert DEFAULT_RETRY_CONFIG["url_network"] == {
            "max_attempts": 3,
            "base_delay": 0.5,
            "max_delay": 10,
        }
        assert DEFAULT_RETRY_CONFIG["audio"] == {
            "max_attempts": 3,
            "base_delay": 2,
            "max_delay": 30,
        }
        assert DEFAULT_RETRY_CONFIG["llm"] == {
            "max_attempts": 3,
            "base_delay": 1,
            "max_delay": 30,
        }
        assert DEFAULT_RETRY_CONFIG["download"] == {
            "max_attempts": 3,
            "base_delay": 1,
            "max_delay": 15,
        }

    def test_get_retry_config_returns_defaults(self):
        """Test get_retry_config returns default values when no overrides."""
        config = get_retry_config("youtube")
        assert config["max_attempts"] == 5
        assert config["base_delay"] == 2
        assert config["max_delay"] == 60

    def test_get_retry_config_unknown_operation(self):
        """Test that unknown operation types fall back to url_network."""
        with patch("content_core.logging.logger") as mock_logger:
            config = get_retry_config("unknown_operation")
            mock_logger.warning.assert_called_once()
            # Should return url_network defaults
            assert config["max_attempts"] == 3
            assert config["base_delay"] == 0.5

    def test_get_retry_config_env_override_max_retries(self):
        """Test environment variable override for max retries."""
        with patch.dict(os.environ, {"CCORE_YOUTUBE_MAX_RETRIES": "10"}):
            config = get_retry_config("youtube")
            assert config["max_attempts"] == 10

    def test_get_retry_config_env_override_base_delay(self):
        """Test environment variable override for base delay."""
        with patch.dict(os.environ, {"CCORE_LLM_BASE_DELAY": "5.5"}):
            config = get_retry_config("llm")
            assert config["base_delay"] == 5.5

    def test_get_retry_config_env_override_max_delay(self):
        """Test environment variable override for max delay."""
        with patch.dict(os.environ, {"CCORE_DOWNLOAD_MAX_DELAY": "100"}):
            config = get_retry_config("download")
            assert config["max_delay"] == 100

    def test_get_retry_config_invalid_max_retries(self):
        """Test that invalid max retries value is ignored."""
        with patch.dict(os.environ, {"CCORE_YOUTUBE_MAX_RETRIES": "100"}):  # > 20
            with patch("content_core.logging.logger") as mock_logger:
                config = get_retry_config("youtube")
                mock_logger.warning.assert_called()
                assert config["max_attempts"] == 5  # Default

    def test_get_retry_config_invalid_base_delay(self):
        """Test that invalid base delay value is ignored."""
        with patch.dict(os.environ, {"CCORE_AUDIO_BASE_DELAY": "not_a_number"}):
            with patch("content_core.logging.logger") as mock_logger:
                config = get_retry_config("audio")
                mock_logger.warning.assert_called()
                assert config["base_delay"] == 2  # Default


class TestRetryDecorators:
    """Tests for retry decorator behavior."""

    @pytest.mark.asyncio
    async def test_retry_youtube_success_first_try(self):
        """Test successful function call on first try."""
        call_count = 0

        @retry_youtube(max_attempts=3)
        async def mock_youtube_call():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_youtube_call()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_youtube_success_after_retry(self):
        """Test successful function call after one retry."""
        call_count = 0

        @retry_youtube(max_attempts=3, base_delay=0.01, max_delay=0.02)
        async def mock_youtube_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise aiohttp.ClientError("Temporary error")
            return "success"

        result = await mock_youtube_call()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_youtube_exhausts_retries(self):
        """Test that function fails after exhausting retries."""
        call_count = 0

        @retry_youtube(max_attempts=3, base_delay=0.01, max_delay=0.02)
        async def mock_youtube_call():
            nonlocal call_count
            call_count += 1
            raise aiohttp.ClientError("Persistent error")

        with pytest.raises(aiohttp.ClientError):
            await mock_youtube_call()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_url_network_retries_on_connection_error(self):
        """Test URL network retry on ConnectionError."""
        call_count = 0

        @retry_url_network(max_attempts=3, base_delay=0.01, max_delay=0.02)
        async def mock_url_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "connected"

        result = await mock_url_call()
        assert result == "connected"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_url_network_retries_on_timeout(self):
        """Test URL network retry on TimeoutError."""
        call_count = 0

        @retry_url_network(max_attempts=2, base_delay=0.01, max_delay=0.02)
        async def mock_url_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timed out")
            return "completed"

        result = await mock_url_call()
        assert result == "completed"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_url_api_success(self):
        """Test URL API retry decorator."""
        call_count = 0

        @retry_url_api(max_attempts=3, base_delay=0.01, max_delay=0.02)
        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("API connection error")
            return {"data": "success"}

        result = await mock_api_call()
        assert result == {"data": "success"}
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_audio_transcription(self):
        """Test audio transcription retry decorator."""
        call_count = 0

        @retry_audio_transcription(max_attempts=3, base_delay=0.01, max_delay=0.02)
        async def mock_transcribe():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Transcription timeout")
            return "transcribed text"

        result = await mock_transcribe()
        assert result == "transcribed text"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_llm_success(self):
        """Test LLM retry decorator."""
        call_count = 0

        @retry_llm(max_attempts=3, base_delay=0.01, max_delay=0.02)
        async def mock_llm_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("LLM API rate limit exceeded")
            return "LLM response"

        result = await mock_llm_call()
        assert result == "LLM response"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_download_success(self):
        """Test download retry decorator."""
        call_count = 0

        @retry_download(max_attempts=3, base_delay=0.01, max_delay=0.02)
        async def mock_download():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise aiohttp.ClientError("Download failed")
            return b"file content"

        result = await mock_download()
        assert result == b"file content"
        assert call_count == 2


class TestLogRetryAttempt:
    """Tests for retry logging."""

    def test_log_retry_attempt_with_exception(self):
        """Test that retry attempts are logged with exception details."""
        mock_state = MagicMock()
        mock_state.fn.__name__ = "test_function"
        mock_state.attempt_number = 2
        mock_state.outcome.exception.return_value = ValueError("Test error")

        with patch("content_core.common.retry.logger") as mock_logger:
            log_retry_attempt(mock_state)
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "Retry 2" in call_args
            assert "test_function" in call_args
            assert "ValueError" in call_args

    def test_log_retry_attempt_no_exception(self):
        """Test logging when no exception is available."""
        mock_state = MagicMock()
        mock_state.fn.__name__ = "test_function"
        mock_state.attempt_number = 1
        mock_state.outcome = None

        with patch("content_core.common.retry.logger") as mock_logger:
            log_retry_attempt(mock_state)
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "unknown error" in call_args


class TestSyncDecorators:
    """Tests for sync function retry decorators."""

    def test_retry_youtube_sync_function(self):
        """Test that retry decorators work with sync functions."""
        call_count = 0

        @retry_youtube(max_attempts=3, base_delay=0.01, max_delay=0.02)
        def mock_sync_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Sync connection error")
            return "sync success"

        result = mock_sync_call()
        assert result == "sync success"
        assert call_count == 2


class TestIsRetryableException:
    """Tests for the is_retryable_exception function."""

    def test_network_errors_are_retryable(self):
        """Test that network-related errors are retryable."""
        assert is_retryable_exception(ConnectionError("Connection refused"))
        assert is_retryable_exception(TimeoutError("Request timed out"))
        assert is_retryable_exception(OSError("Network unreachable"))

    def test_aiohttp_client_error_is_retryable(self):
        """Test that generic aiohttp client errors are retryable."""
        assert is_retryable_exception(aiohttp.ClientError("Client error"))

    def test_permanent_failures_not_retryable(self):
        """Test that permanent failures are not retried."""
        assert not is_retryable_exception(NoTranscriptFound("No transcript"))
        assert not is_retryable_exception(NotFoundError("Resource not found"))
        assert not is_retryable_exception(ValueError("Invalid value"))
        assert not is_retryable_exception(TypeError("Wrong type"))
        assert not is_retryable_exception(KeyError("Missing key"))
        assert not is_retryable_exception(AttributeError("No attribute"))

    def test_generic_exception_with_transient_message_is_retryable(self):
        """Test that generic exceptions with transient-looking messages are retried."""
        assert is_retryable_exception(Exception("Connection timeout"))
        assert is_retryable_exception(Exception("Network unreachable"))
        assert is_retryable_exception(Exception("Service temporarily unavailable"))
        assert is_retryable_exception(Exception("Rate limit exceeded"))
        assert is_retryable_exception(Exception("Too many requests"))
        assert is_retryable_exception(Exception("503 Service Unavailable"))

    def test_generic_exception_without_transient_message_not_retryable(self):
        """Test that generic exceptions without transient indicators are not retried."""
        assert not is_retryable_exception(Exception("Invalid input"))
        assert not is_retryable_exception(Exception("Not found"))
        assert not is_retryable_exception(Exception("Permission denied"))


class TestNoTranscriptFoundNotRetried:
    """Tests that NoTranscriptFound exceptions are not retried."""

    @pytest.mark.asyncio
    async def test_no_transcript_found_not_retried(self):
        """Test that NoTranscriptFound is immediately raised without retry."""
        call_count = 0

        @retry_youtube(max_attempts=5, base_delay=0.01, max_delay=0.02)
        async def mock_transcript_fetch():
            nonlocal call_count
            call_count += 1
            raise NoTranscriptFound("No transcript available for this video")

        with pytest.raises(NoTranscriptFound):
            await mock_transcript_fetch()

        # Should only be called once since NoTranscriptFound is not retryable
        assert call_count == 1


class TestRetryConfigAllOperations:
    """Test retry config for all operation types."""

    @pytest.mark.parametrize(
        "operation_type",
        ["youtube", "url_api", "url_network", "audio", "llm", "download"],
    )
    def test_get_retry_config_all_types(self, operation_type):
        """Test that all operation types return valid config."""
        config = get_retry_config(operation_type)
        assert "max_attempts" in config
        assert "base_delay" in config
        assert "max_delay" in config
        assert isinstance(config["max_attempts"], int)
        assert isinstance(config["base_delay"], (int, float))
        assert isinstance(config["max_delay"], (int, float))
