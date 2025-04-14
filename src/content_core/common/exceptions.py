class ContentCoreError(Exception):
    """Base exception class for Open Notebook errors."""

    pass


class DatabaseOperationError(ContentCoreError):
    """Raised when a database operation fails."""

    pass


class UnsupportedTypeException(ContentCoreError):
    """Raised when an unsupported type is provided."""

    pass


class InvalidInputError(ContentCoreError):
    """Raised when invalid input is provided."""

    pass


class NotFoundError(ContentCoreError):
    """Raised when a requested resource is not found."""

    pass


class AuthenticationError(ContentCoreError):
    """Raised when there's an authentication problem."""

    pass


class ConfigurationError(ContentCoreError):
    """Raised when there's a configuration problem."""

    pass


class ExternalServiceError(ContentCoreError):
    """Raised when an external service (e.g., AI model) fails."""

    pass


class RateLimitError(ContentCoreError):
    """Raised when a rate limit is exceeded."""

    pass


class FileOperationError(ContentCoreError):
    """Raised when a file operation fails."""

    pass


class NetworkError(ContentCoreError):
    """Raised when a network operation fails."""

    pass


class NoTranscriptFound(ContentCoreError):
    """Raised when no transcript is found for a video."""

    pass
