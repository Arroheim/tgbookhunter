"""Tests for JSON cache repository."""

import json
from pathlib import Path

import pytest

from tgbookhunter.domain.models.cache import CachedBook, ScanCache
from tgbookhunter.infrastructure.storage.cache_repository import JsonCacheRepository


@pytest.fixture
def cache_repo(tmp_path: Path) -> JsonCacheRepository:
    """Create a temporary cache repository."""
    return JsonCacheRepository(cache_dir=tmp_path / ".cache")


@pytest.fixture
def sample_cache() -> ScanCache:
    """Create a sample cache with some data."""
    cache = ScanCache(channel_name="test_channel")
    cache.add_book(
        CachedBook(
            message_id=1,
            filename="book1.pdf",
            size_bytes=1024,
            book_format="pdf",
            channel="test_channel",
        )
    )
    cache.add_book(
        CachedBook(
            message_id=5,
            filename="book2.pdf",
            size_bytes=2048,
            book_format="pdf",
            channel="test_channel",
        )
    )
    cache.update_scan_position(10)
    cache.mark_scanned()
    return cache


class TestJsonCacheRepository:
    """Tests for JsonCacheRepository."""

    async def test_save_and_load(
        self, cache_repo: JsonCacheRepository, sample_cache: ScanCache
    ) -> None:
        """Test saving and loading cache."""
        await cache_repo.save(sample_cache)
        loaded = await cache_repo.load("test_channel")

        assert loaded.channel_name == sample_cache.channel_name
        assert loaded.last_scanned_message_id == sample_cache.last_scanned_message_id
        assert len(loaded.books) == len(sample_cache.books)

    async def test_load_nonexistent(self, cache_repo: JsonCacheRepository) -> None:
        """Test loading cache that doesn't exist."""
        cache = await cache_repo.load("nonexistent_channel")
        assert cache.is_empty is True
        assert cache.channel_name == "nonexistent_channel"

    async def test_exists(
        self, cache_repo: JsonCacheRepository, sample_cache: ScanCache
    ) -> None:
        """Test checking if cache exists."""
        assert await cache_repo.exists("test_channel") is False

        await cache_repo.save(sample_cache)
        assert await cache_repo.exists("test_channel") is True

    async def test_delete(
        self, cache_repo: JsonCacheRepository, sample_cache: ScanCache
    ) -> None:
        """Test deleting cache."""
        await cache_repo.save(sample_cache)
        assert await cache_repo.exists("test_channel") is True

        await cache_repo.delete("test_channel")
        assert await cache_repo.exists("test_channel") is False

    async def test_delete_nonexistent(self, cache_repo: JsonCacheRepository) -> None:
        """Test deleting cache that doesn't exist."""
        # Should not raise an error
        await cache_repo.delete("nonexistent_channel")

    async def test_cache_file_naming(self, cache_repo: JsonCacheRepository) -> None:
        """Test that cache files are named correctly."""
        cache = ScanCache(channel_name="@TestChannel")
        await cache_repo.save(cache)

        # Check file exists with correct name
        cache_files = list(cache_repo._cache_dir.glob("*.json"))
        assert len(cache_files) == 1
        assert cache_files[0].name == "testchannel.json"

    async def test_cache_persistence(
        self, cache_repo: JsonCacheRepository, sample_cache: ScanCache
    ) -> None:
        """Test that cache persists to disk correctly."""
        await cache_repo.save(sample_cache)

        # Read file directly
        cache_file = cache_repo._get_cache_path("test_channel")
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)

        assert data["channel_name"] == "test_channel"
        assert len(data["books"]) == 2
