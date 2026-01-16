"""
Retry decorators for handling transient failures in external operations.

This module provides pre-configured retry decorators using tenacity for different
operation types (YouTube, URL extraction, audio transcription, LLM calls, downloads).

Each decorator uses exponential backoff with jitter to prevent thundering herd problems.

Usage:
    from content_core.common.retry import retry_youtube, retry_url_api

    @retry_youtube()
    async def get_video_title(video_id):
        ...

    @retry_url_api()
    async def extract_url_jina(url):
        ...
"""

from typing import Callable, Optional

import aiohttp
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from content_core.common.exceptions import NoTranscriptFound, NotFoundError
from content_core.config import get_retry_config
from content_core.logging import logger


# Exceptions that should NOT be retried (permanent failures)
NON_RETRYABLE_EXCEPTIONS = (
    NoTranscriptFound,
    NotFoundError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


def is_retryable_exception(exception: BaseException) -> bool:
    """
    Determine if an exception should trigger a retry.

    Returns True for transient/network errors, False for permanent failures.
    """
    # Never retry these - they indicate permanent failures
    if isinstance(exception, NON_RETRYABLE_EXCEPTIONS):
        return False

    # Always retry network-related errors
    if isinstance(exception, (aiohttp.ClientError, ConnectionError, TimeoutError, OSError)):
        # But not if it's a client error (4xx) - those are usually permanent
        if isinstance(exception, aiohttp.ClientResponseError):
            status = exception.status
            # Retry server errors (5xx) and rate limits (429)
            return status >= 500 or status == 429
        return True

    # For generic exceptions, check if they look like transient errors
    exc_msg = str(exception).lower()
    transient_indicators = [
        "timeout", "timed out", "connection", "network", "temporary",
        "unavailable", "rate limit", "too many requests", "503", "502", "500"
    ]
    return any(indicator in exc_msg for indicator in transient_indicators)


def log_retry_attempt(retry_state) -> None:
    """
    Log retry attempts with detailed information.

    This is used as the before_sleep callback for tenacity decorators.

    Args:
        retry_state: Tenacity retry state containing attempt info and exception
    """
    func_name = retry_state.fn.__name__ if retry_state.fn else "unknown"
    attempt_num = retry_state.attempt_number
    exception = retry_state.outcome.exception() if retry_state.outcome else None

    if exception:
        exc_type = type(exception).__name__
        exc_msg = str(exception)[:200]  # Truncate long messages
        logger.warning(
            f"Retry {attempt_num} for {func_name}: {exc_type}: {exc_msg}"
        )
    else:
        logger.warning(f"Retry {attempt_num} for {func_name}: unknown error")


def log_retry_exhausted(retry_state) -> None:
    """
    Log when all retry attempts have been exhausted.

    Args:
        retry_state: Tenacity retry state containing final attempt info
    """
    func_name = retry_state.fn.__name__ if retry_state.fn else "unknown"
    attempt_num = retry_state.attempt_number
    exception = retry_state.outcome.exception() if retry_state.outcome else None

    if exception:
        exc_type = type(exception).__name__
        exc_msg = str(exception)[:500]
        logger.error(
            f"All {attempt_num} retries exhausted for {func_name}: {exc_type}: {exc_msg}"
        )
    else:
        logger.error(f"All {attempt_num} retries exhausted for {func_name}")


def retry_youtube(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
) -> Callable:
    """
    Retry decorator for YouTube operations.

    Uses longer delays due to YouTube's aggressive rate limiting.
    Does NOT retry permanent failures like NoTranscriptFound.

    Args:
        max_attempts: Override max retry attempts (default from config: 5)
        base_delay: Override base delay in seconds (default from config: 2)
        max_delay: Override max delay in seconds (default from config: 60)

    Returns:
        Configured tenacity retry decorator
    """
    config = get_retry_config("youtube")
    attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    base = base_delay if base_delay is not None else config["base_delay"]
    max_wait = max_delay if max_delay is not None else config["max_delay"]

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_random_exponential(multiplier=base, max=max_wait),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


def retry_url_api(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
) -> Callable:
    """
    Retry decorator for API-based URL extraction (Jina, Firecrawl).

    Retries on network errors and server errors (5xx, 429), but not client errors (4xx).

    Args:
        max_attempts: Override max retry attempts (default from config: 3)
        base_delay: Override base delay in seconds (default from config: 1)
        max_delay: Override max delay in seconds (default from config: 30)

    Returns:
        Configured tenacity retry decorator
    """
    config = get_retry_config("url_api")
    attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    base = base_delay if base_delay is not None else config["base_delay"]
    max_wait = max_delay if max_delay is not None else config["max_delay"]

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_random_exponential(multiplier=base, max=max_wait),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


def retry_url_network(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
) -> Callable:
    """
    Retry decorator for network-only URL operations (BeautifulSoup, HEAD requests).

    Uses shorter delays as these are typically network-only issues.

    Args:
        max_attempts: Override max retry attempts (default from config: 3)
        base_delay: Override base delay in seconds (default from config: 0.5)
        max_delay: Override max delay in seconds (default from config: 10)

    Returns:
        Configured tenacity retry decorator
    """
    config = get_retry_config("url_network")
    attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    base = base_delay if base_delay is not None else config["base_delay"]
    max_wait = max_delay if max_delay is not None else config["max_delay"]

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_random_exponential(multiplier=base, max=max_wait),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


def retry_audio_transcription(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
) -> Callable:
    """
    Retry decorator for audio transcription (speech-to-text API calls).

    Retries on transient errors, but not on permanent failures like invalid files.

    Args:
        max_attempts: Override max retry attempts (default from config: 3)
        base_delay: Override base delay in seconds (default from config: 2)
        max_delay: Override max delay in seconds (default from config: 30)

    Returns:
        Configured tenacity retry decorator
    """
    config = get_retry_config("audio")
    attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    base = base_delay if base_delay is not None else config["base_delay"]
    max_wait = max_delay if max_delay is not None else config["max_delay"]

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_random_exponential(multiplier=base, max=max_wait),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


def retry_llm(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
) -> Callable:
    """
    Retry decorator for LLM API calls (summary, cleanup).

    Retries on transient errors like rate limits and timeouts, but not on
    permanent failures like invalid API keys or malformed requests.

    Args:
        max_attempts: Override max retry attempts (default from config: 3)
        base_delay: Override base delay in seconds (default from config: 1)
        max_delay: Override max delay in seconds (default from config: 30)

    Returns:
        Configured tenacity retry decorator
    """
    config = get_retry_config("llm")
    attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    base = base_delay if base_delay is not None else config["base_delay"]
    max_wait = max_delay if max_delay is not None else config["max_delay"]

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_random_exponential(multiplier=base, max=max_wait),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


def retry_download(
    max_attempts: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: Optional[float] = None,
) -> Callable:
    """
    Retry decorator for remote file downloads.

    Retries on network errors and server errors (5xx, 429), but not client errors (4xx).

    Args:
        max_attempts: Override max retry attempts (default from config: 3)
        base_delay: Override base delay in seconds (default from config: 1)
        max_delay: Override max delay in seconds (default from config: 15)

    Returns:
        Configured tenacity retry decorator
    """
    config = get_retry_config("download")
    attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    base = base_delay if base_delay is not None else config["base_delay"]
    max_wait = max_delay if max_delay is not None else config["max_delay"]

    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_random_exponential(multiplier=base, max=max_wait),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=log_retry_attempt,
        reraise=True,
    )


# Export RetryError for use in exception handling
__all__ = [
    "retry_youtube",
    "retry_url_api",
    "retry_url_network",
    "retry_audio_transcription",
    "retry_llm",
    "retry_download",
    "log_retry_attempt",
    "log_retry_exhausted",
    "RetryError",
]
