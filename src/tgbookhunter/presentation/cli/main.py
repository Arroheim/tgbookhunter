"""CLI main entry point with rich UI."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tgbookhunter import __version__
from tgbookhunter.application.services.book_hunting_service import BookHuntingService
from tgbookhunter.config.settings import settings
from tgbookhunter.domain.models.models import Book, DownloadTask
from tgbookhunter.infrastructure.storage.cache_repository import JsonCacheRepository
from tgbookhunter.infrastructure.storage.file_storage import (
    BookDownloadService,
    LocalFileStorage,
)
from tgbookhunter.infrastructure.telegram.client import TelegramClientWrapper
from tgbookhunter.presentation.cli.progress import BookHunterProgress

console = Console()


def parse_formats(formats: tuple[str, ...] | None) -> list[str] | None:
    """Convert formats tuple to list or None."""
    return list(formats) if formats else None


def compute_download_stats(download_tasks: list[DownloadTask]) -> dict[str, int]:
    """Calculate download statistics from completed tasks."""
    completed = sum(1 for t in download_tasks if t.status == "completed")
    failed = sum(1 for t in download_tasks if t.status == "failed")
    already_exists = sum(1 for t in download_tasks if t.status == "already_exists")
    return {
        "completed": completed,
        "failed": failed,
        "already_exists": already_exists,
        "actual_downloaded": completed,
    }


def create_services(
    telegram_client: TelegramClientWrapper,
    cache_repo: JsonCacheRepository | None = None,
) -> BookHuntingService:
    """Initialize services with shared Telegram client."""
    storage = LocalFileStorage()
    download_service = BookDownloadService(telegram_client, storage)
    return BookHuntingService(telegram_client, download_service, cache_repo)


async def run_with_telegram(
    channel: str,
    formats_list: list[str] | None,
    cache_repo: JsonCacheRepository | None = None,
) -> tuple[TelegramClientWrapper, BookHuntingService]:
    """Initialize Telegram and services."""
    telegram_client = TelegramClientWrapper()
    console.print("[bold blue]• Connecting to Telegram...[/bold blue]")
    await telegram_client.initialize()
    console.print("[bold green]✓ Connected[/bold green]\n")

    hunting_service = create_services(telegram_client, cache_repo)
    return telegram_client, hunting_service


async def scan_books_with_progress(
    hunting_service: BookHuntingService,
    channel: str,
    formats_list: list[str] | None,
    use_cache: bool = True,
) -> list[Book]:
    """Scan channel for books with live progress indicator."""
    with Live(
        Panel(
            Text("🔍 Scanning channel for books...", style="bold blue"),
            title="📚 Scanning Progress",
            border_style="blue",
        ),
        console=console,
        transient=True,
        refresh_per_second=5,
    ) as live:

        def update_scan_display(count: int) -> None:
            live.update(
                Panel(
                    Text(
                        f"✓ Scanned {count} messages...",
                        style="bold blue",
                    ),
                    title="📚 Scanning Progress",
                    border_style="blue",
                )
            )

        return await hunting_service.list_books(
            channel,
            formats_list,
            use_cache=use_cache,
            scan_progress_callback=update_scan_display,
        )


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """📚 TG Book Hunter - Download books from Telegram channels."""
    pass


@main.command()
@click.argument("channel")
@click.option(
    "-f",
    "--formats",
    multiple=True,
    default=None,
    help="Book formats to download (e.g., pdf, djvu, mobi)",
)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Download directory",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show books without downloading",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Force full re-scan (ignore cache)",
)
def download(
    channel: str,
    formats: tuple[str, ...],
    output: Path | None,
    dry_run: bool,
    no_cache: bool,
) -> None:
    """Download all books from a Telegram channel."""
    formats_list = parse_formats(formats)
    cache_repo = None if no_cache else JsonCacheRepository()

    async def _run() -> None:
        telegram_client = None
        try:
            telegram_client, hunting_service = await run_with_telegram(
                channel, formats_list, cache_repo
            )

            # Show configuration
            table = Table(
                show_header=False,
                box=None,
                padding=(0, 2),
            )
            table.add_column("Param", style="bold")
            table.add_column("Value", justify="right")

            table.add_row("● Channel:", f"@{channel}")
            table.add_row(
                "● Formats:",
                f"{', '.join(formats_list) if formats_list else 'All'}",
            )
            table.add_row("● Output:", str(output or settings.download_dir))
            table.add_row("● Dry run:", "Yes" if dry_run else "No")
            table.add_row("● Cache:", "Disabled" if no_cache else "Enabled")

            console.print()
            console.rule("📚 Book Hunter Configuration", style="blue", align="left")
            console.print()
            console.print(table)
            console.print()

            # Scan for books
            scan_start = datetime.now()
            books = await scan_books_with_progress(
                hunting_service, channel, formats_list, use_cache=not no_cache
            )
            scan_end = datetime.now()
            scan_time = scan_end - scan_start

            if not books:
                action = "found" if dry_run else "to download"
                console.print(f"[yellow]⚠️  No books {action}[/yellow]")
                return

            if dry_run:
                # Display books in a table
                table = Table(
                    title=f"📖 Books found in @{channel}",
                    show_header=True,
                    header_style="bold magenta",
                )
                table.add_column("#", style="dim", width=4)
                table.add_column("Filename", style="cyan")
                table.add_column("Size", justify="right", style="green")
                table.add_column("Format", justify="center")
                table.add_column("Message ID", justify="right")

                for i, book in enumerate(books, 1):
                    table.add_row(
                        str(i),
                        book.filename,
                        book.size.human_readable(),
                        book.format.value.upper(),
                        str(book.message_id),
                    )

                console.print()
                console.print(table)
                console.print(
                    f"\n💾 Total: {len(books)} books, "
                    f"{sum(b.size.mb for b in books):.2f} MB"
                )
            else:
                # Download books with progress
                progress_manager = BookHunterProgress(total_books=len(books))
                progress_manager.set_scan_time(scan_time)
                progress_manager.start()

                try:
                    download_start = datetime.now()
                    download_tasks = await hunting_service.hunt_books(
                        channel,
                        formats=formats_list,
                        download_dir=output,
                        progress_callback=progress_manager.update_task,
                        message_callback=lambda msg: None,
                    )
                    download_end = datetime.now()
                    download_time = download_end - download_start

                    if not download_tasks:
                        console.print("[yellow]⚠️  No books to download[/yellow]")
                        return

                    stats = compute_download_stats(download_tasks)

                finally:
                    progress_manager.set_download_time(download_time)
                    progress_manager.stop()
                    progress_manager.print_summary(
                        completed=stats["actual_downloaded"],
                        failed=stats["failed"],
                        already_exists=stats["already_exists"],
                        download_dir=str(output or settings.download_dir / channel),
                        books=books,
                    )

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Download cancelled by user[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
            logger.exception("Fatal error during download")
            sys.exit(1)
        finally:
            if telegram_client:
                await telegram_client.disconnect()

    asyncio.run(_run())


@main.command()
@click.argument("channel")
@click.option(
    "-f",
    "--formats",
    multiple=True,
    default=None,
    help="Book formats to list",
)
def list_books(channel: str, formats: tuple[str, ...]) -> None:
    """List all books in a Telegram channel without downloading."""
    formats_list = parse_formats(formats)

    async def _run() -> None:
        telegram_client = None
        try:
            telegram_client, hunting_service = await run_with_telegram(
                channel, formats_list
            )

            with console.status("[bold blue]Searching for books...", spinner="dots2"):
                books = await hunting_service.list_books(channel, formats_list)

            if not books:
                console.print("[yellow]⚠️  No books found[/yellow]")
                return

            # Display in table
            table = Table(
                title=f"📖 Books in @{channel}",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("#", style="dim", width=4)
            table.add_column("Filename", style="cyan")
            table.add_column("Size", justify="right", style="green")
            table.add_column("Format", justify="center")
            table.add_column("Description", style="dim", max_width=50)

            for i, book in enumerate(books, 1):
                desc = (book.description or "")[:100] + (
                    "..." if book.description and len(book.description) > 100 else ""
                )
                table.add_row(
                    str(i),
                    book.filename,
                    book.size.human_readable(),
                    book.format.value.upper(),
                    desc,
                )

            console.print()
            console.print(table)
            console.print(
                f"\n📊 Total: {len(books)} books, "
                f"{sum(b.size.mb for b in books):.2f} MB"
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[bold red]❌ Error: {e}[/bold red]")
            sys.exit(1)
        finally:
            if telegram_client:
                await telegram_client.disconnect()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
