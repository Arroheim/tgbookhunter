"""Telegram API client implementation."""

import asyncio
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.types import Channel, DocumentAttributeFilename, Message

from tgbookhunter.config.settings import settings
from tgbookhunter.domain.exceptions.exceptions import (
    DownloadError,
    TelegramConnectionError,
)
from tgbookhunter.domain.models.cache import CachedBook, ScanCache
from tgbookhunter.domain.models.models import (
    Book,
    ChannelInfo,
    TelegramMessage,
)
from tgbookhunter.domain.value_objects.value_objects import (
    BookFormat as BookFormatEnum,
)
from tgbookhunter.domain.value_objects.value_objects import (
    ChannelName,
    FileSize,
)


class TelegramClientWrapper:
    """Wrapper around Telethon client with domain models."""

    def __init__(self) -> None:
        """Initialize Telegram client wrapper."""
        self._client: TelegramClient | None = None
        self._session_name = "tgbookhunter"

    async def initialize(self) -> None:
        """Initialize and authenticate Telegram client."""
        logger.info("Initializing Telegram client...")
        try:
            self._client = TelegramClient(
                self._session_name,
                settings.tg_api_id,
                settings.tg_api_hash,
            )
            await self._client.connect()

            if not await self._client.is_user_authorized():
                logger.info("Authorization required. Sending code request...")
                try:
                    # Send code and wait for user input
                    await self._client.send_code_request(settings.tg_phone)
                    logger.info(f"Code sent to {settings.tg_phone}")

                    # Prompt user for the code
                    code = input("Enter the code you received from Telegram: ")
                    await self._client.sign_in(
                        phone=settings.tg_phone,
                        code=code,
                    )
                    logger.info("Successfully authorized")

                except SessionPasswordNeededError:
                    logger.warning(
                        "Two-step verification enabled. Please provide password."
                    )
                    password = input("Enter your 2FA password: ")
                    await self._client.sign_in(password=password)
                    logger.info("Successfully authorized with 2FA")

            logger.info("Telegram client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            raise TelegramConnectionError(
                message=f"Failed to initialize Telegram client: {e}",
                context={"error_type": type(e).__name__},
            ) from e

    async def disconnect(self) -> None:
        """Disconnect from Telegram."""
        if self._client:
            logger.info("Disconnecting Telegram client...")
            await self._client.disconnect()
            logger.info("Telegram client disconnected")

    async def get_channel_info(self, channel_name: str) -> ChannelInfo:
        """Get information about a Telegram channel."""
        if not self._client:
            raise TelegramConnectionError(message="Client not initialized")

        try:
            logger.info(f"Fetching channel info for @{channel_name}")
            entity = await self._client.get_entity(channel_name)

            if not isinstance(entity, Channel):
                raise TelegramConnectionError(
                    message=f"Entity '{channel_name}' is not a channel",
                    context={"entity_type": type(entity).__name__},
                )

            channel = ChannelName(value=channel_name)
            return ChannelInfo(
                name=channel,
                title=entity.title,
                participants_count=getattr(entity, "participants_count", 0),
                description=getattr(entity, "about", None),
            )
        except FloodWaitError as e:
            logger.warning(f"Rate limited. Waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
            return await self.get_channel_info(channel_name)
        except Exception as e:
            logger.error(f"Failed to get channel info: {e}")
            raise TelegramConnectionError(
                message=f"Failed to get channel info: {e}",
                context={"channel": channel_name, "error_type": type(e).__name__},
            ) from e

    async def iter_messages(
        self,
        channel_name: str,
        limit: int | None = None,
        offset_id: int | None = None,
    ) -> AsyncGenerator[TelegramMessage, None]:
        """Iterate over channel messages and extract book information.

        Args:
            channel_name: Channel to iterate
            limit: Max messages to iterate
            offset_id: Start from message ID (skip messages before this ID)
        """
        if not self._client:
            raise TelegramConnectionError(message="Client not initialized")

        try:
            if offset_id:
                logger.info(
                    f"Iterating messages in @{channel_name} "
                    f"with min_id={offset_id} (skipping older messages)"
                )
            else:
                logger.info(f"Iterating messages in @{channel_name}")

            channel = ChannelName(value=channel_name)

            # KEY FIX: Use min_id instead of offset_id!
            # min_id=X returns messages with ID >= X (newer messages)
            # offset_id returns messages with ID < X (older messages)
            count = 0

            if offset_id is not None:
                async for message in self._client.iter_messages(
                    channel_name,
                    limit=limit,
                    min_id=offset_id,
                ):
                    if not isinstance(message, Message):
                        continue

                    count += 1
                    tg_message = await self._parse_message(message, channel)
                    yield tg_message

                    # Log progress to FILE only (not console to avoid Rich conflicts)
                    if count % 10 == 0:
                        logger.debug(f"Processed {count} new messages...")

                    # Rate limiting
                    if settings.rate_limit_delay > 0:
                        await asyncio.sleep(settings.rate_limit_delay)
            else:
                # Full scan from the beginning
                async for message in self._client.iter_messages(
                    channel_name,
                    limit=limit,
                ):
                    if not isinstance(message, Message):
                        continue

                    count += 1
                    tg_message = await self._parse_message(message, channel)
                    yield tg_message

                    # Log progress to FILE only (not console to avoid Rich conflicts)
                    if count % 50 == 0:
                        logger.debug(f"Processed {count} messages...")

                    # Rate limiting
                    if settings.rate_limit_delay > 0:
                        await asyncio.sleep(settings.rate_limit_delay)

        except FloodWaitError as e:
            logger.warning(f"Rate limited. Waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
            async for msg in self.iter_messages(channel_name, limit=limit):
                yield msg
        except Exception as e:
            logger.error(f"Failed to iterate messages: {e}")
            raise TelegramConnectionError(
                message=f"Failed to iterate messages: {e}",
                context={"channel": channel_name, "error_type": type(e).__name__},
            ) from e

    async def _parse_message(
        self, message: Message, channel: ChannelName
    ) -> TelegramMessage:
        """Parse Telegram message into domain model."""
        has_document = message.document is not None
        document_filename = None
        document_size = None

        if has_document and message.document:
            document_size = message.document.size

            # Try to get filename from document attributes
            for attr in message.document.attributes:
                if isinstance(attr, DocumentAttributeFilename):
                    document_filename = attr.file_name
                    break

            # Fallback to message ID if no filename
            if not document_filename:
                document_filename = f"document_{message.id}"

        return TelegramMessage(
            message_id=message.id,
            channel=channel,
            text=message.text,
            date=message.date,
            has_document=has_document,
            document_filename=document_filename,
            document_size=document_size,
        )

    async def download_document(
        self,
        message_id: int,
        channel_name: str,
        destination: Path,
        progress_callback: Callable[[float], None] | None = None,
    ) -> Path:
        """Download document from Telegram message."""
        if not self._client:
            raise TelegramConnectionError(message="Client not initialized")

        try:
            logger.info(
                f"Downloading document from message {message_id} in @{channel_name}"
            )

            message = await self._client.get_messages(channel_name, ids=message_id)

            if not message or not message.document:
                raise DownloadError(
                    message=f"No document found in message {message_id}",
                    context={"message_id": message_id},
                )

            destination.parent.mkdir(parents=True, exist_ok=True)

            # Download with progress
            def progress_hook(current: int, total: int) -> None:
                if total > 0 and progress_callback:
                    progress = (current / total) * 100
                    progress_callback(progress)

            path = await self._client.download_media(
                message,
                file=str(destination),
                progress_callback=progress_hook if progress_callback else None,
            )

            if not path:
                raise DownloadError(
                    message=f"Failed to download document from message {message_id}",
                    context={"message_id": message_id},
                )

            logger.info(f"Document downloaded to {path}")
            return Path(path)

        except FloodWaitError as e:
            logger.warning(f"Rate limited. Waiting {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)
            return await self.download_document(
                message_id, channel_name, destination, progress_callback
            )
        except Exception as e:
            logger.error(f"Failed to download document: {e}")
            raise DownloadError(
                message=f"Failed to download document: {e}",
                context={
                    "message_id": message_id,
                    "channel": channel_name,
                    "error_type": type(e).__name__,
                },
            ) from e

    async def get_books_from_channel(
        self,
        channel_name: str,
        formats: list[str] | None = None,
        progress_callback: Callable[[int], None] | None = None,
        cache: ScanCache | None = None,
    ) -> tuple[list[Book], ScanCache]:
        """
        Get all books from a channel, optionally filtered by format.

        Uses cache for incremental scanning if available.

        Args:
            channel_name: Telegram channel to search in
            formats: List of book formats to search for
            progress_callback: Callback for scan progress
            cache: Existing cache for incremental scanning

        Returns:
            Tuple of (ALL books for download, updated cache)
        """
        if formats is None:
            formats = settings.book_formats

        # Initialize or use existing cache
        if cache is None:
            cache = ScanCache.empty(channel_name)

        new_cache = ScanCache(
            channel_name=channel_name,
            last_scanned_message_id=cache.last_scanned_message_id,
            books=cache.books.copy(),
        )

        count = 0
        # Key optimization: use offset_id to skip already scanned messages!
        # Telethon will start from messages AFTER offset_id
        start_from = cache.last_scanned_message_id if not cache.is_empty else None

        if start_from:
            logger.info(
                f"Resuming scan from message #{start_from} "
                f"(skipping {cache.last_scanned_message_id} messages)"
            )

        async for message in self.iter_messages(channel_name, offset_id=start_from):
            count += 1

            # Report progress every 10 messages
            if count % 10 == 0 and progress_callback:
                progress_callback(count)

            # Check if message contains a book
            if message.is_book and message.document_filename:
                try:
                    book_format = BookFormatEnum.from_filename(
                        message.document_filename
                    )

                    if book_format.value.lower() in formats:
                        # Add to cache
                        new_cache.add_book(
                            CachedBook(
                                message_id=message.message_id,
                                filename=message.document_filename,
                                size_bytes=message.document_size or 0,
                                book_format=book_format.value,
                                channel=channel_name,
                                description=message.text or "",
                            )
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to parse book from message {message.message_id}: {e}"
                    )
                    continue

            # Update cache position
            new_cache.update_scan_position(message.message_id)

        # Mark scan as complete
        new_cache.mark_scanned()

        # Convert ALL cached books to Book objects for download
        all_books = []
        for cached_book in new_cache.books:
            try:
                book_format = BookFormatEnum(cached_book.book_format)
                book = Book(
                    book_id=f"{channel_name}_{cached_book.message_id}",
                    title=cached_book.filename.rsplit(".", 1)[0],
                    filename=cached_book.filename,
                    format=book_format,
                    size=FileSize(bytes=cached_book.size_bytes),
                    channel=ChannelName(value=cached_book.channel),
                    message_id=cached_book.message_id,
                    description=cached_book.description or None,
                )
                all_books.append(book)
            except ValueError:
                logger.warning(
                    f"Invalid format '{cached_book.book_format}' "
                    f"for {cached_book.filename}"
                )
                continue

        logger.info(
            f"Found {len(all_books)} total books in @{channel_name} "
            f"(cache: {len(cache.books)}, scanned: {count})"
        )
        return all_books, new_cache

    @property
    def client(self) -> TelegramClient | None:
        """Get underlying Telethon client."""
        return self._client
