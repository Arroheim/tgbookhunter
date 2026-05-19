"""Repository interface for book storage."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from tgbookhunter.domain.models.cache import ScanCache
from tgbookhunter.domain.models.models import Book


class BookRepository(ABC):
    """Abstract repository for book persistence."""

    @abstractmethod
    async def save(self, book: Book) -> None:
        """Save a book to storage."""
        pass

    @abstractmethod
    async def find_by_id(self, book_id: str) -> Book | None:
        """Find a book by ID."""
        pass

    @abstractmethod
    async def find_all(self) -> list[Book]:
        """Find all books."""
        pass

    @abstractmethod
    async def find_by_channel(self, channel_name: str) -> list[Book]:
        """Find all books from a specific channel."""
        pass

    @abstractmethod
    async def find_downloaded(self) -> list[Book]:
        """Find all downloaded books."""
        pass

    @abstractmethod
    async def delete(self, book_id: str) -> None:
        """Delete a book from storage."""
        pass


class CacheRepository(ABC):
    """Abstract repository for scan cache persistence."""

    @abstractmethod
    async def load(self, channel_name: str) -> ScanCache:
        """Load cache for a channel."""
        pass

    @abstractmethod
    async def save(self, cache: ScanCache) -> None:
        """Save cache for a channel."""
        pass

    @abstractmethod
    async def delete(self, channel_name: str) -> None:
        """Delete cache for a channel."""
        pass

    @abstractmethod
    async def exists(self, channel_name: str) -> bool:
        """Check if cache exists for a channel."""
        pass


class FileStorage(ABC):
    """Abstract storage for book files."""

    @abstractmethod
    async def download_file(
        self,
        source: str,
        destination: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """Download a file from source to destination."""
        pass

    @abstractmethod
    async def file_exists(self, path: Path) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    async def get_file_size(self, path: Path) -> int:
        """Get file size in bytes."""
        pass

    @abstractmethod
    async def remove_file(self, path: Path) -> None:
        """Remove a file."""
        pass
