"""File storage implementation for downloading books."""

import asyncio
import os
from collections.abc import Callable
from pathlib import Path

from loguru import logger

from tgbookhunter.config.settings import settings
from tgbookhunter.domain.exceptions.exceptions import DownloadError
from tgbookhunter.domain.models.models import Book, DownloadTask
from tgbookhunter.domain.models.repository import FileStorage
from tgbookhunter.infrastructure.telegram.client import TelegramClientWrapper


class LocalFileStorage(FileStorage):
    """Local file system storage implementation."""

    async def download_file(
        self,
        source: str,
        destination: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """
        Download file - this is a placeholder.
        Actual download happens through Telegram client.
        """
        raise NotImplementedError(
            "Use Telegram client to download files, not this storage method"
        )

    async def file_exists(self, path: Path) -> bool:
        """Check if file exists on local filesystem."""
        return path.exists()

    async def get_file_size(self, path: Path) -> int:
        """Get file size from local filesystem."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path.stat().st_size

    async def remove_file(self, path: Path) -> None:
        """Remove file if exists."""
        if path.exists():
            path.unlink()


class BookDownloadService:
    """Service for handling book downloads."""

    def __init__(
        self,
        telegram_client: TelegramClientWrapper,
        storage: FileStorage,
    ) -> None:
        """Initialize download service."""
        self._telegram_client = telegram_client
        self._storage = storage
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        self._max_retries = 3

    async def download_book(
        self,
        book: Book,
        download_dir: Path | None = None,
        progress_callback: Callable[[DownloadTask], None] | None = None,
    ) -> DownloadTask:
        """Download a single book with retry and atomic file operations."""
        if download_dir is None:
            download_dir = settings.download_dir

        task = DownloadTask(
            task_id=f"task_{book.book_id}",
            book=book,
        )

        async with self._semaphore:
            try:
                task.start()
                if progress_callback:
                    progress_callback(task)

                logger.info(
                    f"Downloading: {book.filename} ({book.size.human_readable()})"
                )

                # Create destination path
                dest_path = download_dir / book.channel.value / book.filename
                tmp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")

                # Check if already downloaded
                if await self._storage.file_exists(dest_path):
                    logger.info(f"File already exists: {dest_path}")
                    task.mark_already_exists()
                    if progress_callback:
                        progress_callback(task)
                    return task

                # Remove leftover tmp file if exists
                if await self._storage.file_exists(tmp_path):
                    logger.warning(f"Removing leftover temp file: {tmp_path}")
                    await self._storage.remove_file(tmp_path)

                # Download with retry
                def progress_hook(progress: float) -> None:
                    task.update_progress(progress)
                    if progress_callback:
                        progress_callback(task)

                await self._download_with_retry(book, tmp_path, progress_hook)

                # Atomic rename (tmp → final)
                os.rename(tmp_path, dest_path)

                # Mark as downloaded
                book.mark_as_downloaded(download_dir / book.channel.value)
                task.complete()

                logger.info(
                    f"✓ Downloaded: {book.filename} ({book.size.human_readable()})"
                )

            except Exception as e:
                logger.error(f"✗ Failed to download {book.filename}: {e}")
                task.fail(str(e))

                # Clean up temp file if exists
                if "tmp_path" in locals() and await self._storage.file_exists(tmp_path):
                    await self._storage.remove_file(tmp_path)

            if progress_callback:
                progress_callback(task)

            return task

    async def _download_with_retry(
        self,
        book: Book,
        dest_path: Path,
        progress_hook: Callable[[float], None],
    ) -> None:
        """Download with retry logic and exponential backoff."""
        last_error = None

        for attempt in range(1, self._max_retries + 1):
            try:
                logger.debug(
                    f"Download attempt {attempt}/{self._max_retries} "
                    f"for {book.filename}"
                )

                await self._telegram_client.download_document(
                    message_id=book.message_id,
                    channel_name=book.channel.value,
                    destination=dest_path,
                    progress_callback=progress_hook,
                )

                # Success
                return

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt}/{self._max_retries} failed for "
                    f"{book.filename}: {e}"
                )

                if attempt < self._max_retries:
                    # Exponential backoff: 2s, 4s, 8s
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        raise DownloadError(
            message=f"Failed after {self._max_retries} attempts: {last_error}",
            context={
                "book": book.filename,
                "attempts": self._max_retries,
                "last_error": str(last_error),
            },
        )

    async def download_books(
        self,
        books: list[Book],
        download_dir: Path | None = None,
        progress_callback: Callable[[DownloadTask], None] | None = None,
    ) -> list[DownloadTask]:
        """Download multiple books concurrently."""
        if download_dir is None:
            download_dir = settings.download_dir

        logger.info(f"Starting download of {len(books)} books...")

        # Create tasks for all books
        tasks = [
            self.download_book(book, download_dir, progress_callback) for book in books
        ]

        # Execute all downloads concurrently (limited by semaphore)
        results = await asyncio.gather(*tasks)

        # Summary
        completed = sum(1 for r in results if r.status == "completed")
        failed = sum(1 for r in results if r.status == "failed")

        logger.info(f"Download complete: {completed} succeeded, {failed} failed")

        return list(results)
