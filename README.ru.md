# 📚 TG Book Hunter

[🇬🇧 English](README.md) | 🇷🇺 Русский

CLI-инструмент для автоматического скачивания книг из Telegram каналов с красивым интерфейсом и подробным логированием.

![CI](https://github.com/stanislav-seredkin/tgbookhunter/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

![Demo](demo.gif)

## ✨ Возможности

- 📡 Сканирование Telegram каналов на наличие книг
- 📖 Поддержка форматов: PDF, DJVU, MOBI, EPUB, FB2, CBR, CBZ
- ⚡ Параллельная загрузка с контролем скорости
- 🎨 **Умные прогресс-бары** - общий прогресс + только активные загрузки
- 🔄 **Автоматические retry** при ошибках (3 попытки с exponential backoff)
- 💾 **Инкрементальное кэширование** - быстрое повторное сканирование
- 🔒 **Atomic downloads** - скачивание во временный файл, защита от битых файлов
- 📊 Подробное логирование всех операций
- 🔒 Безопасное хранение API ключей в `.env`
- 🧪 Покрытие тестами
- ✅ Кодстайл проверки (ruff, mypy)

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd tgbookhunter

# Установите зависимости
uv sync
```

### 2. Получение Telegram API ключей

1. Перейдите на https://my.telegram.org/
2. Войдите в свой аккаунт
3. Перейдите в "API development tools"
4. Создайте новое приложение
5. Скопируйте `api_id` и `api_hash`

### 3. Настройка

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
```

Заполните необходимые поля:

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

### 4. Использование

```bash
# Скачать все книги из канала (с кэшированием)
uv run tgbookhunter download @channel_name

# Скачать только PDF и MOBI
uv run tgbookhunter download @channel_name -f pdf -f mobi

# Указать другую директорию для загрузки
uv run tgbookhunter download @channel_name -o /path/to/downloads

# Только посмотреть список книг без скачивания
uv run tgbookhunter download @channel_name --dry-run

# Или использовать команду list
uv run tgbookhunter list @channel_name

# Принудительное полное сканирование (игнорировать кэш)
uv run tgbookhunter download @channel_name --no-cache
```

## 📋 Команды

### `download`

Скачивает все книги из указанного Telegram канала.

```bash
uv run tgbookhunter download <channel> [OPTIONS]
```

**Аргументы:**
- `channel` - Имя Telegram канала (с @ или без)

**Опции:**
- `-f, --formats` - Фильтр по форматам (можно указывать несколько раз)
- `-o, --output` - Директория для загрузки
- `--dry-run` - Показать книги без скачивания
- `--no-cache` - Принудительное полное сканирование (игнорировать кэш)

### `list`

Показывает все книги в канале без скачивания.

```bash
uv run tgbookhunter list <channel> [OPTIONS]
```

**Аргументы:**
- `channel` - Имя Telegram канала

**Опции:**
- `-f, --formats` - Фильтр по форматам

## 🏗️ Архитектура

Проект следует принципам DDD (Domain-Driven Design) и SOLID:

```
src/tgbookhunter/
├── domain/              # Бизнес-логика
│   ├── models/          # Агрегаты: Book, Channel, DownloadTask, ScanCache
│   ├── value_objects/   # Value Objects: FileSize, BookFormat
│   └── exceptions/      # Domain exceptions
├── application/         # Use cases
│   └── services/        # BookHuntingService
├── infrastructure/      # Внешние сервисы
│   ├── telegram/        # Telegram API клиент
│   └── storage/         # File storage, Cache repository
├── presentation/        # UI слой
│   └── cli/             # Click CLI
└── config/              # Настройки
```

## 💾 Кэширование

TG Book Hunter использует инкрементальное кэширование для ускорения повторных запусков:

**Как это работает:**

1. **Первый запуск:** Полное сканирование всех сообщений канала
   ```bash
   uv run tgbookhunter download @channel
   # Сканирование 4900 сообщений... (~8 минут)
   # ✅ Found 15 books, cache saved
   ```

2. **Повторный запуск:** Сканируются только новые сообщения
   ```bash
   uv run tgbookhunter download @channel
   # Cache found - scanning from message #4900...
   # Сканирование 50 новых сообщений... (~секунды)
   # ✅ Found 2 new books (17 total cached)
   ```

3. **Принудительное полное сканирование:**
   ```bash
   uv run tgbookhunter download @channel --no-cache
   # Полное сканирование всех сообщений
   ```

**Где хранится кэш:**
- Файлы в директории `.cache/` (JSON формат)
- Один файл на канал: `.cache/channel_name.json`
- Содержит: позицию сканирования, список книг, timestamp

**Автоматическое обнаружение новых книг:**
- При повторном запуске находятся только новые книги
- Все книги из кэша доступны для скачивания
- Уже скачанные файлы пропускаются автоматически

## 📊 Умные прогресс-бары

При большом количестве книг (2581+) терминал не перегружается:

**Двух-оконный интерфейс:**
- **Верхнее окно (статичное):** Общий прогресс всегда виден, не скролится
- **Нижнее окно (скроллящееся):** Только активные загрузки

```
┌─────────────────────────────────────────────────────────────┐
│ Overall Progress                                            │
│ [██████████████████████████████████░░░░░░░░░░] 1234/2581    │
│ Active: 3 | ✓ 1230 | ✗ 1 | ⏭ 1                              │
└─────────────────────────────────────────────────────────────┘

⬇ Java_Полное_руководство.pdf    [████████████████░░░░] 65.2%
⬇ Python_Cookbook_4th.pdf        [████████░░░░░░░░░░░░] 32.1%
⬇ Clean_Code.pdf                 [████████████████████] 100.0%
```

Completed/Failed автоматически убираются из UI.

**Итоговая статистика после загрузки:**
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

**Новые метрики:**
- **Cache duplicates** - количество книг с одинаковыми именами файлов (одна книга могла загружаться в канал несколько раз)
- **Total size** - общий размер всех файлов для загрузки
- **Scan time** - время, затраченное на сканирование сообщений канала
- **Download time** - время, затраченное на загрузку всех файлов

## 🔄 Retry механизм

**Автоматические повторные попытки:**
- 3 попытки на каждую книгу
- Exponential backoff: 2s → 4s → 8s
- Логирование каждой попытки
- Битые файлы автоматически удаляются

**Atomic downloads:**
- Скачивание во временный файл `.tmp`
- Переименование в целевой файл только после успеха
- Защита от частично скачанных файлов

## 🧪 Разработка

### Запуск тестов

```bash
uv run pytest
uv run pytest --cov=src  # С покрытием
```

### Проверка кода

```bash
# Линтинг
uv run ruff check src/

# Форматирование
uv run ruff format src/

# Проверка типов
uv run mypy src/
```

### Pre-commit хуки

```bash
uv run pre-commit install
```

## 📦 Зависимости

**Основные:**
- `telethon` - Telegram API клиент
- `pydantic` - Валидация данных
- `pydantic-settings` - Управление настройками
- `click` - CLI framework
- `rich` - Прогресс-бары и таблицы
- `loguru` - Логирование
- `aiofiles` - Асинхронная работа с файлами

**Для разработки:**
- `ruff` - Линтер и форматтер
- `mypy` - Проверка типов
- `pytest` - Тестирование
- `pytest-asyncio` - Асинхронные тесты
- `pytest-cov` - Покрытие кода

## ⚙️ Конфигурация

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `TG_API_ID` | Telegram API ID | *обязательный* |
| `TG_API_HASH` | Telegram API Hash | *обязательный* |
| `TG_PHONE` | Номер телефона для авторизации | *обязательный* |
| `DOWNLOAD_DIR` | Директория для загрузки книг | `./downloads` |
| `MAX_CONCURRENT_DOWNLOADS` | Макс. параллельных загрузок | `3` |
| `BOOK_FORMATS` | Форматы книг для поиска | `["pdf", "djvu", "mobi", "epub", "fb2", "cbr", "cbz"]` |
| `RATE_LIMIT_DELAY` | Задержка между запросами (сек) | `0.1` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `LOG_FILE` | Файл логов | `tgbookhunter.log` |

## 🤝 Contributing

1. Форкните репозиторий
2. Создайте ветку для новой фичи (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Add amazing feature'`)
4. Запушьте ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📝 License

MIT License - см. файл [LICENSE](LICENSE) для подробностей.

## ⚠️ Ограничения и риски

### Telegram Rate Limits

Telegram API имеет встроенные ограничения на частоту запросов. При агрессивном использовании:

- **FloodWait** — Telegram может заблокировать запросы на время от нескольких секунд до нескольких часов
- **Бан аккаунта** — при систематических нарушениях лимитов аккаунт может быть временно или постоянно ограничен
- **Рекомендации:**
  - Используйте `RATE_LIMIT_DELAY=0.5` или выше при сканировании больших каналов (10 000+ сообщений)
  - Не запускайте несколько экземпляров одновременно с одним аккаунтом
  - Значение `MAX_CONCURRENT_DOWNLOADS=3` (по умолчанию) — безопасный предел

### Дисклеймер

Этот инструмент предназначен только для личного использования. Убедитесь, что вы соблюдаете:
- Авторские права на скачиваемые материалы
- Правила использования Telegram API
- Законодательство вашей страны

## 🆗 Поддержка

Если у вас возникли проблемы или вопросы:
- Откройте issue в репозитории
- Проверьте логи в файле `tgbookhunter.log`
- Убедитесь, что все зависимости установлены (`uv sync`)
