# 📚 TG Book Hunter

🇬🇧 English | [🇷🇺 Русский](README.ru.md)

A CLI tool for automatically downloading books from Telegram channels, with a beautiful terminal UI and detailed logging.

![CI](https://github.com/Arroheim/tgbookhunter/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

![Demo](demo.gif)

## ✨ Features

- 📡 Scan Telegram channels for books
- 📖 Supported formats: PDF, DJVU, MOBI, EPUB, FB2, CBR, CBZ
- ⚡ Parallel downloads with concurrency control
- 🎨 **Smart progress UI** — overall bar + active downloads only
- 🔄 **Automatic retry** on failure (3 attempts with exponential backoff)
- 💾 **Incremental caching** — re-scans complete in seconds
- 🔒 **Atomic downloads** — temp file renamed on success, no corrupted partials
- 📊 Detailed logging of all operations
- 🔒 API credentials stored safely in `.env`
- 🧪 Test coverage
- ✅ Code quality checks (ruff, mypy)

## 🚀 Quick Start

### 1. Install

```bash
git clone <repository-url>
cd tgbookhunter
uv sync
```

### 2. Get Telegram API credentials

1. Go to https://my.telegram.org/
2. Sign in to your account
3. Navigate to "API development tools"
4. Create a new application
5. Copy `api_id` and `api_hash`

### 3. Configure

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Fill in the required fields:

```env
TG_API_ID=12345
TG_API_HASH=your_api_hash_here
TG_PHONE=+1234567890
DOWNLOAD_DIR=./downloads
MAX_CONCURRENT_DOWNLOADS=3
BOOK_FORMATS=["pdf", "djvu", "mobi", "epub", "fb2", "cbr", "cbz"]
RATE_LIMIT_DELAY=0.1
LOG_LEVEL=INFO
LOG_FILE=tgbookhunter.log
```

### 4. Run

```bash
# Download all books from a channel (with caching)
uv run tgbookhunter download @channel_name

# Download only PDF and MOBI
uv run tgbookhunter download @channel_name -f pdf -f mobi

# Specify a custom download directory
uv run tgbookhunter download @channel_name -o /path/to/downloads

# Preview books without downloading
uv run tgbookhunter download @channel_name --dry-run

# Or use the list command
uv run tgbookhunter list @channel_name

# Force a full re-scan (ignore cache)
uv run tgbookhunter download @channel_name --no-cache
```

## 📋 Commands

### `download`

Download all books from a Telegram channel.

```bash
uv run tgbookhunter download <channel> [OPTIONS]
```

**Arguments:**
- `channel` — Telegram channel name (with or without @)

**Options:**
- `-f, --formats` — Filter by format (can be specified multiple times)
- `-o, --output` — Download directory
- `--dry-run` — List books without downloading
- `--no-cache` — Force full re-scan

### `list`

List all books in a channel without downloading.

```bash
uv run tgbookhunter list <channel> [OPTIONS]
```

**Arguments:**
- `channel` — Telegram channel name

**Options:**
- `-f, --formats` — Filter by format

## 🏗️ Architecture

The project follows DDD (Domain-Driven Design) and SOLID principles:

```
src/tgbookhunter/
├── domain/              # Business logic
│   ├── models/          # Aggregates: Book, Channel, DownloadTask, ScanCache
│   ├── value_objects/   # Value Objects: FileSize, BookFormat
│   └── exceptions/      # Domain exceptions
├── application/         # Use cases
│   └── services/        # BookHuntingService
├── infrastructure/      # External services
│   ├── telegram/        # Telegram API client
│   └── storage/         # File storage, Cache repository
├── presentation/        # UI layer
│   └── cli/             # Click CLI
└── config/              # Settings
```

## 💾 Caching

TG Book Hunter uses incremental caching to speed up repeated runs:

1. **First run:** Full scan of all channel messages
   ```
   Scanning 4900 messages... (~8 minutes)
   ✅ Found 15 books, cache saved
   ```

2. **Subsequent runs:** Only new messages are scanned
   ```
   Cache found — scanning from message #4900...
   Scanning 50 new messages... (~seconds)
   ✅ Found 2 new books (17 total cached)
   ```

3. **Force full re-scan:**
   ```bash
   uv run tgbookhunter download @channel --no-cache
   ```

Cache files are stored in `.cache/` as JSON, one file per channel.

**Already downloaded files are skipped automatically** — so re-running `download` will pick up anything that failed last time without re-downloading what's already there.

## 📊 Progress UI

A dual-window interface keeps the terminal clean for large batches:

```
┌─────────────────────────────────────────────────────────────┐
│ Overall Progress                                            │
│ [██████████████████████████████████░░░░░░░░░░] 1234/2581    │
│ Active: 3 | ✓ 1230 | ✗ 1 | ⏭ 1                              │
└─────────────────────────────────────────────────────────────┘

⬇ Java_Complete_Guide.pdf    [████████████████░░░░] 65.2%
⬇ Python_Cookbook_4th.pdf    [████████░░░░░░░░░░░░] 32.1%
```

- **Top window** — overall progress bar, always visible, never scrolls
- **Bottom window** — active downloads only; completed entries are removed automatically

**Final summary after download:**
```
╭────────────────── 📊 Download Summary ──────────────────╮
│ ■ Total books:           2581                           │
│ ■ Downloaded:            1200                           │
│ ■ Failed:                5                              │
│ ■ Already existed:       1376                           │
│ ■ Cache duplicates:      12                             │
│ ■ Total size:            45.67 GB                       │
│ ⏱ Scan time:            8m 23s                         │
│ ⏱ Download time:        2h 15m 42s                     │
│ ■ Location:              ./downloads/@channel           │
╰─────────────────────────────────────────────────────────╯
```

## 🔄 Retry mechanism

- 3 attempts per file
- Exponential backoff: 2s → 4s → 8s
- Failed partial files are cleaned up automatically
- Downloads go to a `.tmp` file and are atomically renamed on success

## ⚠️ Limitations & Risks

### Telegram Rate Limits

Telegram's API enforces rate limits. Aggressive usage can result in:

- **FloodWait** — requests blocked for seconds to hours
- **Account restrictions** — temporary or permanent limits on the account

**Recommendations:**
- Use `RATE_LIMIT_DELAY=0.5` or higher when scanning large channels (10 000+ messages)
- Don't run multiple instances with the same account simultaneously
- The default `MAX_CONCURRENT_DOWNLOADS=3` is a safe limit

### Disclaimer

This tool is intended for personal use only. Make sure you comply with:
- Copyright law for downloaded materials
- Telegram's Terms of Service and API usage rules
- The legislation of your country

## 🧪 Development

```bash
uv run pytest                # Run tests
uv run pytest --cov=src      # With coverage

uv run ruff check src/       # Lint
uv run ruff format src/      # Format
uv run mypy src/             # Type check

uv run pre-commit install    # Install git hooks
```

## 📦 Dependencies

**Runtime:**
- `telethon` — Telegram API client
- `pydantic` + `pydantic-settings` — data validation and settings
- `click` — CLI framework
- `rich` — progress bars and tables
- `loguru` — logging
- `aiofiles` — async file I/O

**Development:**
- `ruff` — linter and formatter
- `mypy` — static type checking
- `pytest` + `pytest-asyncio` + `pytest-cov` — testing
- `pre-commit` — git hooks

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TG_API_ID` | Telegram API ID | *required* |
| `TG_API_HASH` | Telegram API Hash | *required* |
| `TG_PHONE` | Phone number for auth | *required* |
| `DOWNLOAD_DIR` | Download directory | `./downloads` |
| `MAX_CONCURRENT_DOWNLOADS` | Max parallel downloads | `3` |
| `BOOK_FORMATS` | Formats to search for | `["pdf", "djvu", "mobi", "epub", "fb2", "cbr", "cbz"]` |
| `RATE_LIMIT_DELAY` | Delay between requests (sec) | `0.1` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `tgbookhunter.log` |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

MIT License — see the [LICENSE](LICENSE) file for details.
