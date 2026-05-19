# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-18

### Added
- `download` command — scan a Telegram channel and download all books
- `list` command — list books in a channel without downloading
- Incremental caching via `offset_id` — subsequent scans complete in seconds
- Dual-window progress UI: static overall bar on top, scrollable active downloads below
- Final download summary with total size, scan time, download time, and duplicate count
- Automatic retry with exponential backoff (3 attempts: 2s → 4s → 8s)
- Atomic downloads via `.tmp` files — no corrupted partial files
- Parallel downloads controlled by semaphore (`MAX_CONCURRENT_DOWNLOADS`)
- Support for formats: PDF, DJVU, MOBI, EPUB, FB2, CBR, CBZ
- Configuration via `.env` file (pydantic-settings)
- GitHub Actions CI: ruff, mypy, pytest on Python 3.10 / 3.11 / 3.12
