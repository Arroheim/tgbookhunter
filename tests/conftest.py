"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest

from tgbookhunter.domain.models.models import Book
from tgbookhunter.domain.value_objects.value_objects import (
    BookFormat,
    ChannelName,
    FileSize,
)


@pytest.fixture
def sample_book() -> Book:
    """Create a sample book for testing."""
    return Book(
        book_id="test_1",
        title="Test Book",
        filename="test.pdf",
        format=BookFormat.PDF,
        size=FileSize(bytes=1024),
        channel=ChannelName(value="test_channel"),
        message_id=1,
        description="A test book",
    )


@pytest.fixture
def sample_channel() -> ChannelName:
    """Create a sample channel name."""
    return ChannelName(value="test_channel")


@pytest.fixture
def temp_download_dir(tmp_path: Path) -> Path:
    """Create a temporary download directory."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    return download_dir
