# TG Book Hunter — Архитектура

## Обзор

CLI-инструмент для скачивания книг из Telegram-каналов. Поддерживает форматы PDF, DJVU, MOBI, EPUB, FB2, CBR, CBZ. Ключевые особенности: инкрементальный кэш, параллельная загрузка, умный UI с прогресс-барами.

## Стек

| Компонент | Библиотека |
|-----------|-----------|
| Telegram API | Telethon |
| CLI | Click |
| UI / прогресс-бары | Rich |
| Настройки | pydantic-settings |
| Логирование | Loguru |
| Пакетный менеджер | uv |

## Структура проекта

```
src/tgbookhunter/
├── domain/             # Бизнес-логика, не зависит от внешних библиотек
│   ├── models/         # Book, DownloadTask, ScanCache, CachedBook
│   ├── value_objects/  # FileSize, BookFormat, ChannelName
│   └── exceptions/     # Domain-исключения
├── application/
│   └── services/       # BookHuntingService — оркестрация use cases
├── infrastructure/     # Адаптеры к внешним системам
│   ├── telegram/       # TelegramClientWrapper (Telethon)
│   └── storage/        # BookDownloadService, LocalFileStorage, JsonCacheRepository
├── presentation/
│   └── cli/            # Click-команды + Rich UI (main.py, progress.py)
└── config/             # Settings через pydantic-settings
```

## Команды CLI

```bash
# Скачать все книги из канала
uv run tgbookhunter download @channel_name

# Пропустить кэш, сканировать заново
uv run tgbookhunter download @channel_name --no-cache

# Только посмотреть список книг без скачивания
uv run tgbookhunter list @channel_name
```

## Система кэширования

Позволяет не сканировать весь канал при каждом запуске.

1. **Первый запуск** — полное сканирование всех сообщений (~8 мин для 5000 сообщений)
2. **Повторный запуск** — сканируются только новые сообщения (~секунды)
3. Кэш хранится в `.cache/{channel}.json`
4. Флаг `--no-cache` принудительно запускает полное сканирование

Ключевой механизм: Telethon `offset_id` позволяет начать итерацию с последнего просканированного сообщения, полностью пропуская уже обработанные.

```json
{
  "channel_name": "bookofgeek",
  "last_scanned_message_id": 4921,
  "scanned_at": "2026-04-12T17:50:00",
  "total_messages_scanned": 4921,
  "books": [
    {
      "message_id": 4890,
      "filename": "book.pdf",
      "size_bytes": 1234567,
      "book_format": "pdf",
      "channel": "bookofgeek"
    }
  ]
}
```

## UI: прогресс-бары

Двух-оконный интерфейс для работы с большим количеством книг:

```
┌──────────────────────────────────────────────────────┐
│ Overall Progress                                      │
│ [██████████████████████████░░░░] 1234/2581            │
│ Active: 3 | ✓ 1230 | ✗ 1 | ⏭ 1                       │
└──────────────────────────────────────────────────────┘

⬇ Java_Guide.pdf      [████████████████░░] 65.2% • 59.8 MB
⬇ Python_Cookbook.pdf [████████░░░░░░░░░░] 32.1% • 12.3 MB
```

- **Верхнее окно** — общий прогресс, статичное, не скролится
- **Нижнее окно** — только активные загрузки; завершённые исчезают автоматически

По завершении выводится итоговая статистика: количество скачанных/пропущенных/упавших файлов, общий размер, время сканирования и загрузки.

## Загрузка файлов

**Параллельность** — ограничена `asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)`.

**Retry с exponential backoff:**
- 3 попытки на каждый файл
- Задержки: 2s → 4s → 8s
- При исчерпании попыток — ошибка с логированием

**Атомарность:**
- Скачивание идёт во временный файл `.tmp`
- После успеха — `os.rename()` в целевой путь
- При ошибке — `.tmp` удаляется, итоговый файл не создаётся

**Пропуск уже скачанных** — перед загрузкой проверяется наличие финального файла на ФС. Если файл есть — задача помечается как `already_exists` и пропускается. Это означает, что повторный запуск `download` автоматически доберёт всё, что не скачалось в прошлый раз.

## Разработка

```bash
uv sync --group dev          # Установить зависимости

uv run pytest                # Тесты (70 штук)
uv run pytest --cov=src      # С покрытием

uv run ruff check src/       # Линтинг
uv run ruff format src/      # Форматирование
uv run mypy src/             # Проверка типов

uv run pre-commit install    # Установить хуки
```

## CI

GitHub Actions запускается на каждый push/PR в `main`:
- **check** — ruff lint, ruff format, mypy
- **test** — pytest на Python 3.10, 3.11, 3.12

## Статус

- ✅ Сканирование и скачивание книг из Telegram-каналов
- ✅ Инкрементальный кэш через `offset_id`
- ✅ Параллельные загрузки с семафором
- ✅ Retry с exponential backoff + атомарные загрузки
- ✅ Dual-window UI (Rich) + итоговая статистика
- ✅ 70 тестов, ruff и mypy без ошибок
- ✅ GitHub Actions CI (Python 3.10 / 3.11 / 3.12)
