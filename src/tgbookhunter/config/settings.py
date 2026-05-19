"""Configuration management using pydantic-settings."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram API credentials
    tg_api_id: int = Field(..., description="Telegram API ID")
    tg_api_hash: str = Field(..., description="Telegram API Hash")
    tg_phone: str = Field(..., description="Phone number for Telegram auth")

    # Download settings
    download_dir: Path = Field(
        default=Path("./downloads"),
        description="Directory to download books to",
    )
    max_concurrent_downloads: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent downloads",
    )

    # Book formats
    book_formats: list[str] = Field(
        default=["pdf", "djvu", "mobi", "epub", "fb2", "cbr", "cbz"],
        description="List of book formats to search for",
    )

    # Rate limiting
    rate_limit_delay: float = Field(
        default=0.1,
        ge=0.0,
        description="Delay between requests in seconds",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )
    log_file: str = Field(
        default="tgbookhunter.log",
        description="Log file path",
    )

    @field_validator("tg_api_id")
    @classmethod
    def validate_api_id(cls, v: int) -> int:
        """Validate that API ID is positive."""
        if v <= 0:
            raise ValueError("TG_API_ID must be a positive integer")
        return v

    @field_validator("tg_api_hash")
    @classmethod
    def validate_api_hash(cls, v: str) -> str:
        """Validate that API hash is not empty."""
        if not v or v == "your_api_hash_here":
            raise ValueError("TG_API_HASH must be set to a valid value")
        return v

    @field_validator("tg_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate that phone number is not empty."""
        if not v or v == "your_phone_number_here":
            raise ValueError("TG_PHONE must be set to a valid phone number")
        return v

    @field_validator("download_dir")
    @classmethod
    def validate_download_dir(cls, v: Path) -> Path:
        """Ensure download directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v


# Global settings instance
settings = Settings()  # type: ignore[call-arg]
