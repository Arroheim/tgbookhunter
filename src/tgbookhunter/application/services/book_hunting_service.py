"""Application service for orchestrating book hunting operations."""

from collections.abc import Callable
from pathlib import Path

from loguru import logger

from tgbookhunter.config.settings import settings
from tgbookhunter.domain.exceptions.exceptions import (
    TelegramConnectionError,
)
from tgbookhunter.domain.models.cache import ScanCache
from tgbookhunter.domain.models.models import Book, DownloadTask
from tgbookhunter.domain.models.repository import CacheRepository
from tgbookhunter.infrastructure.storage.file_storage import BookDownloadService
from tgbookhunter.infrastructure.telegram.client import TelegramClientWrapper


class BookHuntingService:
    """
    Application service that coordinates finding and downloading books.

    This is the main use case orchestrator following DDD principles.
    """

    def __init__(
        self,
        telegram_client: TelegramClientWrapper,
        download_service: BookDownloadService,
        cache_repo: CacheRepository | None = None,
    ) -> None:
        """Initialize book hunting service."""
        self._telegram_client = telegram_client
        self._download_service = download_service
        self._cache_repo = cache_repo

    async def hunt_books(
        self,
        channel_name: str,
        formats: list[str] | None = None,
        download_dir: Path | None = None,
        progress_callback: Callable[[DownloadTask], None] | None = None,
        message_callback: Callable[[str], None] | None = None,
        scan_progress_callback: Callable[[int], None] | None = None,
        use_cache: bool = True,
    ) -> list[DownloadTask]:
        """
        Main use case: Find all books in a channel and download them.

        Args:
            channel_name: Telegram channel to search in
            formats: List of book formats to search for (defaults to settings)
            download_dir: Directory to download books to
            progress_callback: Callback for download progress updates
            message_callback: Callback for status messages
            scan_progress_callback: Callback for scan progress (message count)
            use_cache: Whether to use cached scan results

        Returns:
            List of download tasks with their statuses
        """
        if download_dir is None:
            download_dir = settings.download_dir

        if message_callback:
            message_callback("📡 Connecting to Telegram...")

        # Ensure we're connected to Telegram
        if not self._telegram_client.client:
            await self._telegram_client.initialize()

        # Load cache if available
        cache = ScanCache.empty(channel_name)
        if use_cache and self._cache_repo:
            cache = await self._cache_repo.load(channel_name)
            if cache.is_empty:
                if message_callback:
                    message_callback("📚 First scan - scanning all messages...")
            else:
                if message_callback:
                    message_callback(
                        f"📚 Cache found - scanning from message "
                        f"#{cache.last_scanned_message_id}..."
                    )

        if message_callback:
            message_callback(f"📚 Scanning channel @{channel_name}...")

        # Get channel info
        try:
            channel_info = await self._telegram_client.get_channel_info(channel_name)
            logger.info(
                f"Channel: {channel_info.title or channel_info.name.value}, "
                f"Participants: {channel_info.participants_count}"
            )
            if message_callback:
                message_callback(
                    f"📊 Channel: {channel_info.title or channel_info.name.value} "
                    f"({channel_info.participants_count} participants)"
                )
        except TelegramConnectionError as e:
            logger.error(f"Failed to get channel info: {e}")
            if message_callback:
                message_callback(f"❌ Error: {e.message}")
            raise

        # Find all books (incremental if cache exists)
        if message_callback:
            message_callback("🔍 Searching for books...")

        books, new_cache = await self._telegram_client.get_books_from_channel(
            channel_name, formats, scan_progress_callback, cache
        )

        # Save updated cache
        if use_cache and self._cache_repo and new_cache:
            await self._cache_repo.save(new_cache)

        if not books:
            logger.warning(f"No books found in @{channel_name}")
            if message_callback:
                message_callback("⚠️ No books found matching the criteria")
            return []

        logger.info(f"Found {len(books)} books in @{channel_name}")
        if message_callback:
            message_callback(f"✅ Found {len(books)} books")

            # Show book list
            for i, book in enumerate(books, 1):
                message_callback(
                    f"  {i}. {book.filename} ({book.size.human_readable()})"
                )

        # Download all books
        if message_callback:
            message_callback(f"⬇️ Starting download of {len(books)} books...")

        download_tasks = await self._download_service.download_books(
            books,
            download_dir=download_dir,
            progress_callback=progress_callback,
        )

        # Summary
        completed = sum(1 for task in download_tasks if task.status == "completed")
        failed = sum(1 for task in download_tasks if task.status == "failed")

        if message_callback:
            message_callback(
                f"\n{'=' * 50}\n"
                f"📦 Download Summary:\n"
                f"  ✅ Success: {completed}\n"
                f"  ❌ Failed: {failed}\n"
                f"  📁 Location: {download_dir / channel_name}\n"
                f"{'=' * 50}"
            )

        return download_tasks

    async def list_books(
        self,
        channel_name: str,
        formats: list[str] | None = None,
        use_cache: bool = True,
        scan_progress_callback: Callable[[int], None] | None = None,
    ) -> list[Book]:
        """
        List all books in a channel without downloading.

        Args:
            channel_name: Telegram channel to search in
            formats: List of book formats to search for
            use_cache: Whether to use cached scan results
            scan_progress_callback: Callback for scan progress

        Returns:
            List of found books
        """
        if not self._telegram_client.client:
            await self._telegram_client.initialize()

        # Load cache if available
        cache = ScanCache.empty(channel_name)
        if use_cache and self._cache_repo:
            cache = await self._cache_repo.load(channel_name)

        books, new_cache = await self._telegram_client.get_books_from_channel(
            channel_name, formats, scan_progress_callback, cache
        )

        # Save updated cache
        if use_cache and self._cache_repo and new_cache:
            await self._cache_repo.save(new_cache)

        logger.info(f"Listed {len(books)} books in @{channel_name}")
        return books

