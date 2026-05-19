"""Tests for cache model."""

from datetime import datetime

from tgbookhunter.domain.models.cache import CachedBook, ScanCache


class TestCachedBook:
    """Tests for CachedBook model."""

    def test_creation(self) -> None:
        """Test CachedBook creation."""
        book = CachedBook(
            message_id=123,
            filename="test.pdf",
            size_bytes=1024,
            book_format="pdf",
            channel="test_channel",
        )
        assert book.message_id == 123
        assert book.filename == "test.pdf"
        assert book.size_bytes == 1024
        assert book.book_format == "pdf"
        assert book.channel == "test_channel"

    def test_to_dict(self) -> None:
        """Test CachedBook serialization."""
        book = CachedBook(
            message_id=123,
            filename="test.pdf",
            size_bytes=1024,
            book_format="pdf",
            channel="test_channel",
        )
        data = book.to_dict()
        assert data == {
            "message_id": 123,
            "filename": "test.pdf",
            "size_bytes": 1024,
            "book_format": "pdf",
            "channel": "test_channel",
            "description": "",
        }

    def test_from_dict(self) -> None:
        """Test CachedBook deserialization."""
        data = {
            "message_id": 123,
            "filename": "test.pdf",
            "size_bytes": 1024,
            "book_format": "pdf",
            "channel": "test_channel",
            "description": "Test book",
        }
        book = CachedBook.from_dict(data)
        assert book.message_id == 123
        assert book.filename == "test.pdf"
        assert book.size_bytes == 1024
        assert book.book_format == "pdf"
        assert book.channel == "test_channel"
        assert book.description == "Test book"


class TestScanCache:
    """Tests for ScanCache model."""

    def test_empty_cache(self) -> None:
        """Test creating empty cache."""
        cache = ScanCache.empty("test_channel")
        assert cache.channel_name == "test_channel"
        assert cache.last_scanned_message_id == 0
        assert cache.is_empty is True
        assert len(cache.books) == 0

    def test_add_book(self) -> None:
        """Test adding a book to cache."""
        cache = ScanCache.empty("test_channel")
        book = CachedBook(
            message_id=1,
            filename="test.pdf",
            size_bytes=1024,
            book_format="pdf",
            channel="test_channel",
        )
        cache.add_book(book)

        assert len(cache.books) == 1
        assert cache.books[0] == book
        assert 1 in cache.book_message_ids

    def test_add_duplicate_book(self) -> None:
        """Test adding duplicate book is ignored."""
        cache = ScanCache.empty("test_channel")
        book1 = CachedBook(
            message_id=1,
            filename="test.pdf",
            size_bytes=1024,
            book_format="pdf",
            channel="test_channel",
        )
        book2 = CachedBook(
            message_id=1,
            filename="test2.pdf",
            size_bytes=2048,
            book_format="pdf",
            channel="test_channel",
        )

        cache.add_book(book1)
        cache.add_book(book2)

        assert len(cache.books) == 1
        assert cache.books[0] == book1

    def test_update_scan_position(self) -> None:
        """Test updating scan position."""
        cache = ScanCache.empty("test_channel")
        cache.update_scan_position(10)
        cache.update_scan_position(5)  # Should not decrease
        cache.update_scan_position(20)

        assert cache.last_scanned_message_id == 20
        assert cache.total_messages_scanned == 3

    def test_mark_scanned(self) -> None:
        """Test marking cache as scanned."""
        cache = ScanCache.empty("test_channel")
        assert cache.scanned_at is None

        cache.mark_scanned()
        assert cache.scanned_at is not None
        assert isinstance(cache.scanned_at, datetime)

    def test_to_dict(self) -> None:
        """Test ScanCache serialization."""
        cache = ScanCache.empty("test_channel")
        cache.add_book(
            CachedBook(
                message_id=1,
                filename="test.pdf",
                size_bytes=1024,
                book_format="pdf",
                channel="test_channel",
            )
        )
        cache.update_scan_position(100)
        cache.mark_scanned()

        data = cache.to_dict()
        assert data["channel_name"] == "test_channel"
        assert data["last_scanned_message_id"] == 100
        assert data["total_messages_scanned"] == 1
        assert len(data["books"]) == 1
        assert data["scanned_at"] is not None

    def test_from_dict(self) -> None:
        """Test ScanCache deserialization."""
        data = {
            "channel_name": "test_channel",
            "last_scanned_message_id": 100,
            "scanned_at": "2026-04-12T12:00:00",
            "total_messages_scanned": 100,
            "books": [
                {
                    "message_id": 1,
                    "filename": "test.pdf",
                    "size_bytes": 1024,
                    "book_format": "pdf",
                    "channel": "test_channel",
                    "description": "Test book",
                }
            ],
        }
        cache = ScanCache.from_dict(data)

        assert cache.channel_name == "test_channel"
        assert cache.last_scanned_message_id == 100
        assert cache.total_messages_scanned == 100
        assert len(cache.books) == 1
        assert cache.books[0].message_id == 1
        assert cache.books[0].book_format == "pdf"

    def test_merge(self) -> None:
        """Test merging two caches."""
        cache1 = ScanCache.empty("test_channel")
        cache1.add_book(
            CachedBook(
                message_id=1,
                filename="book1.pdf",
                size_bytes=1024,
                book_format="pdf",
                channel="test_channel",
            )
        )
        # Simulate scanning 50 messages
        for i in range(1, 51):
            cache1.update_scan_position(i)

        cache2 = ScanCache.empty("test_channel")
        cache2.add_book(
            CachedBook(
                message_id=2,
                filename="book2.pdf",
                size_bytes=2048,
                book_format="pdf",
                channel="test_channel",
            )
        )
        # Simulate scanning 50 more messages (51-100)
        for i in range(51, 101):
            cache2.update_scan_position(i)

        cache1.merge(cache2)

        assert len(cache1.books) == 2
        assert cache1.last_scanned_message_id == 100
        assert cache1.total_messages_scanned == 100  # 50 + 50
