"""Value objects for the domain."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from tgbookhunter.domain.exceptions.exceptions import InvalidBookFormatError


class BookFormat(Enum):
    """Supported book formats."""

    PDF = "pdf"
    DJVU = "djvu"
    MOBI = "mobi"
    EPUB = "epub"
    FB2 = "fb2"
    CBR = "cbr"
    CBZ = "cbz"

    @classmethod
    def from_filename(cls, filename: str) -> "BookFormat":
        """Determine book format from filename."""
        extension = Path(filename).suffix.lower().lstrip(".")
        try:
            return cls(extension)
        except ValueError as e:
            raise InvalidBookFormatError(
                message=f"Unsupported book format: {extension}",
                context={"filename": filename, "extension": extension},
            ) from e

    @classmethod
    def is_book_format(cls, filename: str) -> bool:
        """Check if filename has a book format extension."""
        try:
            cls.from_filename(filename)
            return True
        except InvalidBookFormatError:
            return False


@dataclass(frozen=True)
class FileSize:
    """Value object representing file size."""

    bytes: int

    def __post_init__(self) -> None:
        """Validate file size."""
        if self.bytes < 0:
            raise ValueError("File size cannot be negative")

    @property
    def kb(self) -> float:
        """Convert to kilobytes."""
        return self.bytes / 1024

    @property
    def mb(self) -> float:
        """Convert to megabytes."""
        return self.bytes / (1024 * 1024)

    @property
    def gb(self) -> float:
        """Convert to gigabytes."""
        return self.bytes / (1024 * 1024 * 1024)

    def human_readable(self) -> str:
        """Return human-readable file size string."""
        if self.gb >= 1:
            return f"{self.gb:.2f} GB"
        elif self.mb >= 1:
            return f"{self.mb:.2f} MB"
        elif self.kb >= 1:
            return f"{self.kb:.2f} KB"
        else:
            return f"{self.bytes} bytes"


@dataclass(frozen=True)
class ChannelName:
    """Value object for Telegram channel name."""

    value: str

    def __post_init__(self) -> None:
        """Validate channel name."""
        if not self.value or not self.value.strip():
            raise ValueError("Channel name cannot be empty")
        # Remove @ prefix if present
        object.__setattr__(self, "value", self.value.lstrip("@"))

    def __str__(self) -> str:
        """Return channel name without @."""
        return self.value

    def with_at(self) -> str:
        """Return channel name with @ prefix."""
        return f"@{self.value}"
