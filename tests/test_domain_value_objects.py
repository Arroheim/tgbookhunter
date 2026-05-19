"""Tests for domain value objects."""

import pytest

from tgbookhunter.domain.value_objects.value_objects import (
    BookFormat,
    ChannelName,
    FileSize,
)


class TestBookFormat:
    """Tests for BookFormat enum."""

    def test_from_filename_pdf(self) -> None:
        """Test PDF format detection."""
        fmt = BookFormat.from_filename("book.pdf")
        assert fmt == BookFormat.PDF

    def test_from_filename_djvu(self) -> None:
        """Test DJVU format detection."""
        fmt = BookFormat.from_filename("book.djvu")
        assert fmt == BookFormat.DJVU

    def test_from_filename_mobi(self) -> None:
        """Test MOBI format detection."""
        fmt = BookFormat.from_filename("book.mobi")
        assert fmt == BookFormat.MOBI

    def test_from_filename_epub(self) -> None:
        """Test EPUB format detection."""
        fmt = BookFormat.from_filename("book.epub")
        assert fmt == BookFormat.EPUB

    def test_from_filename_fb2(self) -> None:
        """Test FB2 format detection."""
        fmt = BookFormat.from_filename("book.fb2")
        assert fmt == BookFormat.FB2

    def test_from_filename_cbr(self) -> None:
        """Test CBR format detection."""
        fmt = BookFormat.from_filename("book.cbr")
        assert fmt == BookFormat.CBR

    def test_from_filename_cbz(self) -> None:
        """Test CBZ format detection."""
        fmt = BookFormat.from_filename("book.cbz")
        assert fmt == BookFormat.CBZ

    def test_from_filename_case_insensitive(self) -> None:
        """Test format detection is case insensitive."""
        fmt = BookFormat.from_filename("book.PDF")
        assert fmt == BookFormat.PDF

    def test_from_filename_invalid_format(self) -> None:
        """Test invalid format raises exception."""
        from tgbookhunter.domain.exceptions.exceptions import InvalidBookFormatError

        with pytest.raises(InvalidBookFormatError):
            BookFormat.from_filename("book.txt")

    def test_is_book_format_true(self) -> None:
        """Test valid book format detection."""
        assert BookFormat.is_book_format("book.pdf") is True

    def test_is_book_format_false(self) -> None:
        """Test non-book format detection."""
        assert BookFormat.is_book_format("photo.jpg") is False


class TestFileSize:
    """Tests for FileSize value object."""

    def test_bytes(self) -> None:
        """Test bytes property."""
        size = FileSize(bytes=1024)
        assert size.bytes == 1024

    def test_kb(self) -> None:
        """Test kilobytes conversion."""
        size = FileSize(bytes=2048)
        assert size.kb == 2.0

    def test_mb(self) -> None:
        """Test megabytes conversion."""
        size = FileSize(bytes=1048576)
        assert size.mb == 1.0

    def test_gb(self) -> None:
        """Test gigabytes conversion."""
        size = FileSize(bytes=1073741824)
        assert size.gb == 1.0

    def test_human_readable_bytes(self) -> None:
        """Test human-readable format for small files."""
        size = FileSize(bytes=512)
        assert size.human_readable() == "512 bytes"

    def test_human_readable_kb(self) -> None:
        """Test human-readable format for KB."""
        size = FileSize(bytes=2048)
        assert size.human_readable() == "2.00 KB"

    def test_human_readable_mb(self) -> None:
        """Test human-readable format for MB."""
        size = FileSize(bytes=5242880)
        assert size.human_readable() == "5.00 MB"

    def test_human_readable_gb(self) -> None:
        """Test human-readable format for GB."""
        size = FileSize(bytes=2147483648)
        assert size.human_readable() == "2.00 GB"

    def test_negative_size_raises_error(self) -> None:
        """Test negative size raises ValueError."""
        with pytest.raises(ValueError, match="cannot be negative"):
            FileSize(bytes=-1)


class TestChannelName:
    """Tests for ChannelName value object."""

    def test_simple_name(self) -> None:
        """Test simple channel name."""
        channel = ChannelName(value="mychannel")
        assert channel.value == "mychannel"
        assert str(channel) == "mychannel"

    def test_name_with_at_prefix(self) -> None:
        """Test channel name with @ prefix is stripped."""
        channel = ChannelName(value="@mychannel")
        assert channel.value == "mychannel"
        assert str(channel) == "mychannel"

    def test_with_at_method(self) -> None:
        """Test with_at method adds @ prefix."""
        channel = ChannelName(value="mychannel")
        assert channel.with_at() == "@mychannel"

    def test_empty_name_raises_error(self) -> None:
        """Test empty name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChannelName(value="")

    def test_whitespace_only_raises_error(self) -> None:
        """Test whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ChannelName(value="   ")
