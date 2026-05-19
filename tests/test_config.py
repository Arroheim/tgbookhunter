"""Tests for configuration settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from tgbookhunter.config.settings import Settings


class TestSettings:
    """Tests for Settings model."""

    def test_settings_require_api_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TG_API_ID is required."""
        monkeypatch.delenv("TG_API_ID", raising=False)
        monkeypatch.delenv("TG_API_HASH", raising=False)
        monkeypatch.delenv("TG_PHONE", raising=False)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    def test_settings_require_api_hash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TG_API_HASH is required."""
        monkeypatch.delenv("TG_API_HASH", raising=False)
        monkeypatch.delenv("TG_PHONE", raising=False)
        with pytest.raises(ValidationError):
            Settings(tg_api_id=12345, _env_file=None)

    def test_settings_require_phone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TG_PHONE is required."""
        monkeypatch.delenv("TG_PHONE", raising=False)
        with pytest.raises(ValidationError):
            Settings(tg_api_id=12345, tg_api_hash="test_hash", _env_file=None)

    def test_settings_default_values(self) -> None:
        """Test settings default values."""
        settings = Settings(
            tg_api_id=12345,
            tg_api_hash="test_hash",
            tg_phone="+1234567890",
            _env_file=None,  # Ignore .env file
        )

        assert settings.download_dir == Path("./downloads")
        assert settings.max_concurrent_downloads == 3
        assert settings.rate_limit_delay == 0.1
        assert settings.log_level == "INFO"
        assert settings.book_formats == [
            "pdf",
            "djvu",
            "mobi",
            "epub",
            "fb2",
            "cbr",
            "cbz",
        ]

    def test_settings_custom_values(self, tmp_path: Path) -> None:
        """Test settings with custom values."""
        download_dir = tmp_path / "custom_downloads"

        settings = Settings(
            tg_api_id=12345,
            tg_api_hash="test_hash",
            tg_phone="+1234567890",
            download_dir=download_dir,
            max_concurrent_downloads=5,
            rate_limit_delay=2.0,
            log_level="DEBUG",
        )

        assert settings.download_dir == download_dir
        assert settings.max_concurrent_downloads == 5
        assert settings.rate_limit_delay == 2.0
        assert settings.log_level == "DEBUG"

    def test_settings_invalid_api_id(self) -> None:
        """Test that negative API ID raises error."""
        with pytest.raises(ValidationError, match="positive integer"):
            Settings(
                tg_api_id=-1,
                tg_api_hash="test_hash",
                tg_phone="+1234567890",
            )

    def test_settings_invalid_api_hash_placeholder(self) -> None:
        """Test that placeholder API hash raises error."""
        with pytest.raises(ValidationError, match="must be set to a valid value"):
            Settings(
                tg_api_id=12345,
                tg_api_hash="your_api_hash_here",
                tg_phone="+1234567890",
            )

    def test_settings_invalid_phone_placeholder(self) -> None:
        """Test that placeholder phone raises error."""
        with pytest.raises(
            ValidationError, match="must be set to a valid phone number"
        ):
            Settings(
                tg_api_id=12345,
                tg_api_hash="test_hash",
                tg_phone="your_phone_number_here",
            )

    def test_settings_creates_download_dir(self, tmp_path: Path) -> None:
        """Test that download directory is created if it doesn't exist."""
        download_dir = tmp_path / "new_downloads"

        settings = Settings(
            tg_api_id=12345,
            tg_api_hash="test_hash",
            tg_phone="+1234567890",
            download_dir=download_dir,
        )

        assert settings.download_dir.exists()

    def test_settings_max_concurrent_downloads_limits(self) -> None:
        """Test max_concurrent_downloads upper limit."""
        with pytest.raises(ValidationError):
            Settings(
                tg_api_id=12345,
                tg_api_hash="test_hash",
                tg_phone="+1234567890",
                max_concurrent_downloads=11,
            )

    def test_settings_max_concurrent_downloads_minimum(self) -> None:
        """Test max_concurrent_downloads lower limit."""
        with pytest.raises(ValidationError):
            Settings(
                tg_api_id=12345,
                tg_api_hash="test_hash",
                tg_phone="+1234567890",
                max_concurrent_downloads=0,
            )
