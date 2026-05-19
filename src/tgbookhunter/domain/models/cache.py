"""Cache model for storing scan results."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CachedBook:
    """Represents a cached book entry with full information."""

    message_id: int
    filename: str
    size_bytes: int
    book_format: str  # pdf, djvu, mobi, etc.
    channel: str
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CachedBook":
        """Create CachedBook from dictionary."""
        return cls(
            message_id=data["message_id"],
            filename=data["filename"],
            size_bytes=data["size_bytes"],
            book_format=data["book_format"],
            channel=data["channel"],
            description=data.get("description", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "message_id": self.message_id,
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "book_format": self.book_format,
            "channel": self.channel,
            "description": self.description,
        }


@dataclass
class ScanCache:
    """
    Cache for channel scan results.

    Stores information about already scanned messages and found books
    to avoid re-scanning the entire channel on subsequent runs.
    """

    channel_name: str
    last_scanned_message_id: int = 0
    scanned_at: datetime | None = None
    total_messages_scanned: int = 0
    books: list[CachedBook] = field(default_factory=list)

    @property
    def book_message_ids(self) -> set[int]:
        """Get set of message IDs that contain books."""
        return {book.message_id for book in self.books}

    @property
    def is_empty(self) -> bool:
        """Check if cache is empty (no scan performed yet)."""
        return self.last_scanned_message_id == 0

    def add_book(self, book: CachedBook) -> None:
        """Add a book to cache, avoiding duplicates."""
        if book.message_id not in self.book_message_ids:
            self.books.append(book)

    def update_scan_position(self, message_id: int) -> None:
        """Update the last scanned message ID."""
        self.last_scanned_message_id = max(
            self.last_scanned_message_id,
            message_id,
        )
        self.total_messages_scanned += 1

    def mark_scanned(self) -> None:
        """Mark the cache as having a completed scan."""
        self.scanned_at = datetime.now()

    def merge(self, other: "ScanCache") -> None:
        """Merge another cache into this one."""
        for book in other.books:
            self.add_book(book)
        self.last_scanned_message_id = max(
            self.last_scanned_message_id,
            other.last_scanned_message_id,
        )
        self.total_messages_scanned += other.total_messages_scanned
        if other.scanned_at and (
            not self.scanned_at or other.scanned_at > self.scanned_at
        ):
            self.scanned_at = other.scanned_at

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScanCache":
        """Create ScanCache from dictionary."""
        return cls(
            channel_name=data["channel_name"],
            last_scanned_message_id=data.get("last_scanned_message_id", 0),
            scanned_at=(
                datetime.fromisoformat(data["scanned_at"])
                if data.get("scanned_at")
                else None
            ),
            total_messages_scanned=data.get("total_messages_scanned", 0),
            books=[
                CachedBook.from_dict(b) for b in data.get("books", [])
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "channel_name": self.channel_name,
            "last_scanned_message_id": self.last_scanned_message_id,
            "scanned_at": self.scanned_at.isoformat() if self.scanned_at else None,
            "total_messages_scanned": self.total_messages_scanned,
            "books": [book.to_dict() for book in self.books],
        }

    @classmethod
    def empty(cls, channel_name: str) -> "ScanCache":
        """Create an empty cache for a channel."""
        return cls(channel_name=channel_name)
