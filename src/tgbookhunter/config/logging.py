"""Logging configuration for the entire application."""

from loguru import logger

from tgbookhunter.config.settings import settings


def setup_logging() -> None:
    """Configure loguru logger - file only, no console output."""
    logger.remove()

    logger.add(
        settings.log_file,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
        "{name}:{function}:{line} - {message}",
        rotation="20 MB",
        retention="1 week",
        encoding="utf-8",
    )
