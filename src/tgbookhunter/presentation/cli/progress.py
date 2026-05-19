"""Improved progress manager with dual-window layout."""

from datetime import timedelta

from rich.console import Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
)
from rich.table import Table

from tgbookhunter.domain.models.models import Book, DownloadTask


class BookHunterProgress:
    """
    Dual-window progress manager for book downloads.

    Layout:
    ┌─────────────────────────────────────────┐
    │  Overall Progress (static, always visible) │
    └─────────────────────────────────────────┘
    ┌─────────────────────────────────────────┐
    │                                         │
    │  Active Downloads (scrollable)          │
    │                                         │
    └─────────────────────────────────────────┘
    """

    def __init__(self, total_books: int) -> None:
        """Initialize progress manager.

        Args:
            total_books: Total number of books to download
        """
        self._total = total_books
        self._completed = 0
        self._failed = 0
        self._already_existed = 0
        self._active = 0

        # Timing
        self._scan_time: timedelta | None = None
        self._download_time: timedelta | None = None

        # Overall progress (static)
        self._overall_progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=50),
            TextColumn("[bold]{task.completed}/{task.total}"),
            TextColumn("[dim]•[/dim]"),
            TextColumn("[dim]{task.fields[status]}[/dim]"),
        )

        self._overall_task_id = self._overall_progress.add_task(
            "[bold blue]Overall Progress",
            total=total_books,
            status="Starting...",
        )

        # Individual download progress (scrollable)
        self._download_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.fields[filename]}"),
            BarColumn(bar_width=30),
            "[progress.percentage]{task.percentage:>3.1f}%",
            "•",
            DownloadColumn(),
        )

        self._task_map: dict[str, TaskID] = {}

        # Live display with dual layout
        self._live: Live | None = None
        self._group = Group(
            self._overall_progress,
            self._download_progress,
        )

    def start(self) -> None:
        """Start progress display."""
        self._live = Live(
            self._group,
            console=self._overall_progress.console,
            refresh_per_second=10,
            screen=False,
        )
        self._live.start()

    def stop(self) -> None:
        """Stop progress display."""
        if self._live:
            self._live.stop()

    def _update_overall_status(self) -> None:
        """Update overall progress status."""
        status = (
            f"⚡ Active: {self._active} | "
            f"✓ Done: {self._completed} | ✗ Failed: {self._failed} | "
            f"⧉ Duplicate: {self._already_existed}"
        )
        self._overall_progress.update(
            self._overall_task_id,
            status=status,
        )

    def add_task(self, task: DownloadTask) -> None:
        """Add a new download task to progress display."""
        task_id = self._download_progress.add_task(
            "download",
            total=task.book.size.bytes,
            filename=task.book.filename,
        )
        self._task_map[task.task_id] = task_id
        self._active += 1
        self._update_overall_status()

    def update_task(self, task: DownloadTask) -> None:
        """Update progress for a download task."""
        if task.task_id not in self._task_map:
            self.add_task(task)

        task_id = self._task_map[task.task_id]

        if task.status == "downloading":
            # Update intermediate progress
            downloaded_bytes = (task.progress / 100.0) * task.book.size.bytes
            self._download_progress.update(
                task_id,
                completed=downloaded_bytes,
            )

        elif task.status == "completed":
            self._download_progress.update(
                task_id,
                completed=task.book.size.bytes,
            )
            self._completed += 1
            self._active -= 1

            # Remove from active display
            try:
                self._download_progress.remove_task(task_id)
                del self._task_map[task.task_id]
            except KeyError:
                pass

        elif task.status == "failed":
            self._failed += 1
            self._active -= 1

            # Remove from active display
            try:
                self._download_progress.remove_task(task_id)
                del self._task_map[task.task_id]
            except KeyError:
                pass

        elif task.status == "already_exists":
            self._already_existed += 1
            self._active -= 1

            # Remove from active display
            try:
                self._download_progress.remove_task(task_id)
                del self._task_map[task.task_id]
            except KeyError:
                pass

        # Update overall progress
        advance = 1 if task.status in [
            "completed",
            "failed",
            "already_exists",
        ] else 0
        self._overall_progress.update(
            self._overall_task_id,
            advance=advance,
        )
        self._update_overall_status()

    def set_scan_time(self, scan_time: timedelta) -> None:
        """Set the scan duration for summary display."""
        self._scan_time = scan_time

    def set_download_time(self, download_time: timedelta) -> None:
        """Set the download duration for summary display."""
        self._download_time = download_time

    def print_summary(
        self,
        completed: int,
        failed: int,
        already_exists: int,
        download_dir: str,
        books: list[Book] | None = None,
    ) -> None:
        """Print final summary after stopping Live display."""
        console = self._overall_progress.console

        # Create summary table
        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
        )
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("■ Total books", str(self._total))
        table.add_row("[green]■[/green] Downloaded", f"[green]{completed}[/green]")
        table.add_row("[red]■[/red] Failed", f"[red]{failed}[/red]")
        table.add_row(
            "[yellow]■[/yellow] Already existed",
            f"[yellow]{already_exists}[/yellow]",
        )

        # Add duplicates count from cache
        if books:
            # Count duplicates (books with same filename)
            filename_counts: dict[str, int] = {}
            for book in books:
                filename_counts[book.filename] = (
                    filename_counts.get(book.filename, 0) + 1
                )
            duplicates = sum(1 for count in filename_counts.values() if count > 1)
            if duplicates > 0:
                table.add_row(
                    "[magenta]■[/magenta] Cache duplicates",
                    f"[magenta]{duplicates}[/magenta]",
                )

            # Add total size
            total_size_bytes = sum(book.size.bytes for book in books)
            total_size_mb = total_size_bytes / (1024 * 1024)
            if total_size_mb >= 1024:
                size_str = f"{total_size_mb / 1024:.2f} GB"
            else:
                size_str = f"{total_size_mb:.2f} MB"
            table.add_row("■ Total size", size_str)

        # Add timing information
        if self._scan_time:
            scan_seconds = self._scan_time.total_seconds()
            if scan_seconds >= 60:
                scan_str = f"{int(scan_seconds // 60)}m {int(scan_seconds % 60)}s"
            else:
                scan_str = f"{scan_seconds:.1f}s"
            table.add_row("⏱ Scan time", scan_str)

        if self._download_time:
            dl_seconds = self._download_time.total_seconds()
            if dl_seconds >= 60:
                dl_str = f"{int(dl_seconds // 60)}m {int(dl_seconds % 60)}s"
            else:
                dl_str = f"{dl_seconds:.1f}s"
            table.add_row("⏱ Download time", dl_str)

        table.add_row("■ Location", download_dir)

        # Print summary
        console.print()
        console.rule(
            "📊 Download Summary",
            style="green" if failed == 0 else "yellow",
            align="left",
        )
        console.print()
        console.print(table)
        console.print()
