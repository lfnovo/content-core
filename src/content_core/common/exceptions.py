"""Typed exceptions that can escape ``extract_content``.

Every class here has a real raise site (or is the base callers catch). Per
the raise/degrade boundary in ``ARCHITECTURE.md``, total failure raises one
of these; degradation only exists within a single source.
"""


class ContentCoreError(Exception):
    """Base exception for content-core errors."""

    pass


class UnsupportedTypeException(ContentCoreError):
    """Raised when a file/MIME type is not one we route."""

    pass


class InvalidInputError(ContentCoreError):
    """Raised when no source is provided, or the input is malformed."""

    pass


class ConfigurationError(ContentCoreError):
    """Raised when a configuration cannot be honored."""

    pass


class NotFoundError(ContentCoreError):
    """Raised when a requested resource is not found."""

    pass


class NoTranscriptFound(ContentCoreError):
    """Raised when no usable transcript is found for a video."""

    pass


class NetworkError(ContentCoreError):
    """Raised on a connection, timeout, or DNS failure."""

    pass


class ExternalServiceError(ContentCoreError):
    """Raised when an external service fails.

    Covers Firecrawl, Jina, STT and LLM providers, including their
    authentication and rate-limit responses -- the caller's remedy is the
    same in every case (check the provider); the message carries the detail.
    """

    pass


class FileOperationError(ContentCoreError):
    """Raised when a routed file exists but parsing or processing failed."""

    pass
