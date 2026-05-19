"""JSON file-based cache repository implementation."""

import json
from pathlib import Path

from loguru import logger

from tgbookhunter.domain.models.cache import ScanCache
from tgbookhunter.domain.models.repository import CacheRepository


class JsonCacheRepository(CacheRepository):
    """JSON file-based cache repository."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Initialize cache repository.

        Args:
            cache_dir: Directory to store cache files. Defaults to .cache/
        """
        if cache_dir is None:
            cache_dir = Path(".cache")
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, channel_name: str) -> Path:
        """Get cache file path for a channel."""
        # Sanitize channel name for file system
        safe_name = channel_name.lstrip("@").lower()
        return self._cache_dir / f"{safe_name}.json"

    async def load(self, channel_name: str) -> ScanCache:
        """Load cache for a channel."""
        cache_path = self._get_cache_path(channel_name)

        if not cache_path.exists():
            logger.debug(f"No cache found for @{channel_name}")
            return ScanCache.empty(channel_name)

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)
            cache = ScanCache.from_dict(data)
            logger.info(
                f"Loaded cache for @{channel_name}: "
                f"{cache.last_scanned_message_id} messages, "
                f"{len(cache.books)} books"
            )
            return cache
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load cache for @{channel_name}: {e}")
            return ScanCache.empty(channel_name)

    async def save(self, cache: ScanCache) -> None:
        """Save cache for a channel."""
        cache_path = self._get_cache_path(cache.channel_name)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache.to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(
                f"Saved cache for @{cache.channel_name}: "
                f"{cache.last_scanned_message_id} messages, "
                f"{len(cache.books)} books"
            )
        except OSError as e:
            logger.error(f"Failed to save cache for @{cache.channel_name}: {e}")

    async def delete(self, channel_name: str) -> None:
        """Delete cache for a channel."""
        cache_path = self._get_cache_path(channel_name)

        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.info(f"Deleted cache for @{channel_name}")
            except OSError as e:
                logger.error(f"Failed to delete cache for @{channel_name}: {e}")
        else:
            logger.debug(f"No cache to delete for @{channel_name}")

    async def exists(self, channel_name: str) -> bool:
        """Check if cache exists for a channel."""
        return self._get_cache_path(channel_name).exists()
