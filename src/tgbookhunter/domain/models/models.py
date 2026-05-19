"""Domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from tgbookhunter.domain.value_objects.value_objects import (
    BookFormat,
    ChannelName,
    FileSize,
)


@dataclass
class TelegramMessage:
    """Domain model representing a Telegram message."""

    message_id: int
    channel: ChannelName
    text: str | None = None
    date: datetime | None = None
    has_document: bool = False
    document_filename: str | None = None
    document_size: int | None = None

    @property
    def is_book(self) -> bool:
        """Check if message contains a book file."""
        if not self.has_document or not self.document_filename:
            return False
        return BookFormat.is_book_format(self.document_filename)


@dataclass
class Book:
    """Domain model representing a downloadable book."""

    book_id: str
    title: str
    filename: str
    format: BookFormat
    size: FileSize
    channel: ChannelName
    message_id: int
    description: str | None = None
    download_path: Path | None = None
    is_downloaded: bool = False
    downloaded_at: datetime | None = None

    @property
    def full_path(self) -> Path | None:
        """Get full path to downloaded file."""
        if self.download_path:
            return self.download_path / self.filename
        return None

    def mark_as_downloaded(self, download_path: Path) -> None:
        """Mark book as downloaded."""
        self.download_path = download_path
        self.is_downloaded = True
        self.downloaded_at = datetime.now()


@dataclass
class DownloadTask:
    """Domain model representing a book download task."""

    task_id: str
    book: Book
    status: str = "pending"  # pending, downloading, completed, failed
    progress: float = 0.0  # 0.0 to 100.0
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def start(self) -> None:
        """Mark task as started."""
        self.status = "downloading"
        self.started_at = datetime.now()
        self.progress = 0.0

    def update_progress(self, progress: float) -> None:
        """Update download progress."""
        if not 0 <= progress <= 100:
            raise ValueError("Progress must be between 0 and 100")
        self.progress = progress

    def complete(self) -> None:
        """Mark task as completed."""
        self.status = "completed"
        self.progress = 100.0
        self.completed_at = datetime.now()
        self.book.mark_as_downloaded(self.book.download_path or Path("./downloads"))

    def mark_already_exists(self) -> None:
        """Mark task as already downloaded (file exists)."""
        self.status = "already_exists"
        self.progress = 100.0
        self.completed_at = datetime.now()
        self.book.mark_as_downloaded(self.book.download_path or Path("./downloads"))

    def fail(self, error_message: str) -> None:
        """Mark task as failed."""
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = datetime.now()


@dataclass
class ChannelInfo:
    """Domain model representing Telegram channel information."""

    name: ChannelName
    title: str | None = None
    participants_count: int = 0
    description: str | None = None
    books_count: int = 0
    books: list[Book] = field(default_factory=list)

    def add_book(self, book: Book) -> None:
        """Add a book to the channel's book list."""
        self.books.append(book)
        self.books_count = len(self.books)
