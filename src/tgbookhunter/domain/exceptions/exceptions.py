"""Base domain exception."""

from typing import Any


class DomainError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        self.message = message
        self.context = context or {}
        super().__init__(self.message)


class BookNotFoundError(DomainError):
    """Raised when a book file cannot be found."""

    pass


class InvalidBookFormatError(DomainError):
    """Raised when a book format is not supported."""

    pass


class DownloadError(DomainError):
    """Raised when a book download fails."""

    pass


class TelegramConnectionError(DomainError):
    """Raised when Telegram connection fails."""

    pass


class RateLimitError(DomainError):
    """Raised when rate limit is exceeded."""

    pass
