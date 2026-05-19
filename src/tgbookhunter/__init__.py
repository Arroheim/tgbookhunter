"""TG Book Hunter - CLI tool for downloading books from Telegram channels."""

__version__ = "0.1.0"

# Configure logging once at package import
from tgbookhunter.config.logging import setup_logging

setup_logging()
