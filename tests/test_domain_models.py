"""Tests for domain models."""

from pathlib import Path

import pytest

from tgbookhunter.domain.models.models import (
    Book,
    ChannelInfo,
    DownloadTask,
    TelegramMessage,
)
from tgbookhunter.domain.value_objects.value_objects import (
    BookFormat,
    ChannelName,
    FileSize,
)


class TestTelegramMessage:
    """Tests for TelegramMessage model."""

    def test_message_without_document(self) -> None:
        """Test message without document."""
        msg = TelegramMessage(
            message_id=1,
            channel=ChannelName(value="test"),
            text="Hello",
        )
        assert msg.is_book is False

    def test_message_with_book_file(self) -> None:
        """Test message with book file."""
        msg = TelegramMessage(
            message_id=1,
            channel=ChannelName(value="test"),
            has_document=True,
            document_filename="book.pdf",
            document_size=1024,
        )
        assert msg.is_book is True

    def test_message_with_non_book_file(self) -> None:
        """Test message with non-book file."""
        msg = TelegramMessage(
            message_id=1,
            channel=ChannelName(value="test"),
            has_document=True,
            document_filename="photo.jpg",
            document_size=1024,
        )
        assert msg.is_book is False


class TestBook:
    """Tests for Book model."""

    def test_book_creation(self) -> None:
        """Test book creation."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        assert book.book_id == "test_1"
        assert book.is_downloaded is False
        assert book.download_path is None

    def test_full_path_when_downloaded(self) -> None:
        """Test full path when book is downloaded."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
            download_path=Path("/downloads"),
        )
        assert book.full_path == Path("/downloads/test.pdf")

    def test_full_path_when_not_downloaded(self) -> None:
        """Test full path is None when not downloaded."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        assert book.full_path is None

    def test_mark_as_downloaded(self) -> None:
        """Test marking book as downloaded."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )

        download_dir = Path("/downloads")
        book.mark_as_downloaded(download_dir)

        assert book.is_downloaded is True
        assert book.download_path == download_dir
        assert book.downloaded_at is not None


class TestDownloadTask:
    """Tests for DownloadTask model."""

    def test_initial_state(self) -> None:
        """Test initial task state."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        task = DownloadTask(task_id="task_1", book=book)

        assert task.status == "pending"
        assert task.progress == 0.0
        assert task.error_message is None
        assert task.started_at is None

    def test_start_task(self) -> None:
        """Test starting a download task."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        task = DownloadTask(task_id="task_1", book=book)
        task.start()

        assert task.status == "downloading"
        assert task.progress == 0.0
        assert task.started_at is not None

    def test_update_progress(self) -> None:
        """Test updating task progress."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        task = DownloadTask(task_id="task_1", book=book)
        task.update_progress(50.0)

        assert task.progress == 50.0

    def test_update_progress_invalid_too_high(self) -> None:
        """Test updating progress with value > 100 raises error."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        task = DownloadTask(task_id="task_1", book=book)

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            task.update_progress(101.0)

    def test_update_progress_invalid_negative(self) -> None:
        """Test updating progress with negative value raises error."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        task = DownloadTask(task_id="task_1", book=book)

        with pytest.raises(ValueError, match="must be between 0 and 100"):
            task.update_progress(-1.0)

    def test_complete_task(self) -> None:
        """Test completing a download task."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        task = DownloadTask(task_id="task_1", book=book)
        task.start()
        task.complete()

        assert task.status == "completed"
        assert task.progress == 100.0
        assert task.completed_at is not None
        assert book.is_downloaded is True

    def test_fail_task(self) -> None:
        """Test failing a download task."""
        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )
        task = DownloadTask(task_id="task_1", book=book)
        task.fail("Download failed")

        assert task.status == "failed"
        assert task.error_message == "Download failed"
        assert task.completed_at is not None


class TestChannelInfo:
    """Tests for ChannelInfo model."""

    def test_channel_info_creation(self) -> None:
        """Test channel info creation."""
        info = ChannelInfo(
            name=ChannelName(value="test"),
            title="Test Channel",
            participants_count=1000,
            description="A test channel",
        )
        assert info.name.value == "test"
        assert info.title == "Test Channel"
        assert info.participants_count == 1000
        assert info.books_count == 0

    def test_add_book(self) -> None:
        """Test adding a book to channel info."""
        info = ChannelInfo(name=ChannelName(value="test"))

        book = Book(
            book_id="test_1",
            title="Test Book",
            filename="test.pdf",
            format=BookFormat.PDF,
            size=FileSize(bytes=1024),
            channel=ChannelName(value="test"),
            message_id=1,
        )

        info.add_book(book)

        assert info.books_count == 1
        assert len(info.books) == 1
        assert info.books[0] == book
