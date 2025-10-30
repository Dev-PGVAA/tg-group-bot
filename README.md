Да, теперь всё ясно. Проект, который вы используете, **отличается** от оригинального `tg-group-bot` на GitHub, описанного в README. Ваша версия — это **модифицированная**, с добавленными модулями `forwarder.py` (на Telethon) и `sil_bot.py` (на python-telegram-bot), а также с изменённой структурой. Я обновил `README.md`, чтобы он соответствовал **вашей** текущей реализации.

---

### **Файл: `README.md` (обновлённый)**

```markdown
# tg-group-bot (Модифицированная версия с Forwarder и Sil_Bot)

> ⚠️ **Важно:** Этот репозиторий содержит _модифицированную версию_ оригинального `tg-group-bot`. Структура и функциональность были значительно изменены.

Асинхронный Telegram-бот для управления группами с веб-панелью на FastAPI.

- **Защищенная веб-панель** с системой авторизации
- **Мониторинг в реальном времени** - статус ботов, логи, uptime
- **Управление Telegram-каналами** - автоматическая пересылка сообщений (через Forwarder)
- **Управление Telegram-группами** - трекинг упражнений (через Sil_Bot)
- **Централизованное логирование** в стиле uvicorn
- ⚡ **Асинхронная архитектура** для высокой производительности
- **Модульная структура** - легко расширять функционал
- **Фоновый запуск** с автоматическим управлением
- **Гибкая конфигурация** через`.env`или`config.json`

---

## 📁 Структура проекта
```

tg-group-bot/
├── src/
│ ├── config.py # Конфигурация проекта (API_ID, TOKEN, GROUP_ID и т.д.)
│ ├── logger.py # Унифицированный логгер
│ ├── utils/ # Вспомогательные функции
│ │ └── utils.py # load_json, save_json, ensure_dir, record_stat
│ ├── webpanel/ # Веб-панель (FastAPI)
│ │ ├── webpanel.py # Основной файл веб-панели
│ │ ├── static/ # Статические файлы (CSS, JS)
│ │ └── templates/ # HTML-шаблоны для веб-панели
│ └── bot/ # Telegram боты (разные модули)
│ ├── forwarder.py # (Telethon) Юзер-бот для пересылки сообщений из каналов
│ ├── sil_bot.py # (python-telegram-bot) Бот для трекинга упражнений
│ └── error_reporter.py # Отправка ошибок админу
├── data/
│ ├── logs/ # Логи всех компонентов
│ │ ├── bot.log # Логи Telegram ботов
│ │ ├── webpanel.log # Логи веб-панели
│ │ ├── forwarder_subprocess.log # Логи подпроцесса Forwarder
│ │ ├── sil_subprocess.log # Логи подпроцесса Sil_Bot
│ │ └── sil_errors.log # Ошибки бота (из error_reporter)
│ ├── channels.json # Список каналов для Forwarder
│ ├── stats.json # Статистика пересылок (Forwarder)
│ ├── records.json # Записи упражнений (Sil_Bot)
│ └── users.json # Данные пользователей (авторизация)
├── venv/ # Виртуальное окружение
├── requirements.txt # Python зависимости
├── .env # Конфигурация (создайте из примера)
└── README.md

````

---

## 🚀 Установка

```bash
git clone https://github.com/Dev-PGVAA/tg-group-bot.git
cd tg-group-bot
````

### Установка виртуального окружения

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate
# Windows
python -m venv venv
venv\Scripts\activate
```

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Конфигурация

Создайте файл `.env` или `config.json`:

#### **Вариант 1: .env файл** (рекомендуется)

```env
# Telegram (для Sil_Bot)
BOT_TOKEN=your_bot_token_from_botfather
# Telegram (для Forwarder)
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
SESSION_NAME=session.session
# Целевая группа для Forwarder
GROUP_ID=-1001234567890
TOPIC_FORWARD=0 # ID топика (0 если не используется)
# Web Panel
WEB_HOST=0.0.0.0
WEB_PORT=9000
# Logging
WEB_LOG=data/logs/webpanel.log
CHANNELS_FILE=data/channels.json
STATS_FILE=data/stats.json
RECORDS_FILE=data/records.json
```

#### **Вариант 2: config.json**

```json
{
	"BOT_TOKEN": "your_bot_token",
	"API_ID": 12345678,
	"API_HASH": "your_api_hash",
	"SESSION_NAME": "session.session",
	"GROUP_ID": -1001234567890,
	"TOPIC_FORWARD": 0,
	"WEB_HOST": "0.0.0.0",
	"WEB_PORT": 9000,
	"WEB_LOG": "data/logs/webpanel.log",
	"CHANNELS_FILE": "data/channels.json",
	"STATS_FILE": "data/stats.json",
	"RECORDS_FILE": "data/records.json"
}
```

---

## 🎯 Функциональность

### 1. **Веб-панель (FastAPI)**

- Управление ботами `Forwarder` и `Sil_Bot` (запуск, остановка, перезапуск).
- Просмотр логов подпроцессов.
- Редактирование списка каналов (`channels.json`).
- Редактирование записей тренировок (`records.json`).
- Защита доступа (авторизация).

### 2. **Forwarder Bot (Telethon)**

- Подписывается на каналы из `channels.json`.
- Пересылает сообщения из отслеживаемых каналов в указанную `GROUP_ID`.
- Использует `SESSION_NAME` для подключения (юзер-бот).
- Сохраняет статистику пересылок в `stats.json`.
- Обрабатывает `/channels` команды в целевой группе для управления каналами.

### 3. **Sil_Bot (python-telegram-bot)**

- Бот для трекинга физических упражнений.
- Команды: `/help`, `/sil`, `/top`, `/table`.
- Сохраняет записи в `records.json`.

---

## 📦 Запуск

### Способ 1: Через веб-панель (рекомендуется)

1. Запустите веб-панель:
   ```bash
   python -m src.webpanel.webpanel
   ```
2. Откройте браузер: `http://localhost:9000` (или ваш `WEB_HOST:WEB_PORT`).
3. Войдите (по умолчанию `admin` / `admin123`) и **сразу смените пароль**.
4. Используйте веб-интерфейс для запуска/остановки `Forwarder` и `Sil_Bot`.

### Способ 2: Прямой запуск подпроцессов (не рекомендуется)

- `Forwarder`: `python -m src.bot.forwarder`
- `Sil_Bot`: `python -m src.bot.sil_bot`

> ⚠️ Прямой запуск не рекомендуется, так как веб-панель управляет ими как подпроцессами.

---

## 🖥️ Веб-панель

- **Адрес:** `http://localhost:9000/admin`

---

## 📝 Логирование

Все логи сохраняются в папке `data/logs/` в едином стиле:

```
INFO  : 2025-10-24 22:15:01 - Starting bot process...
INFO  : 2025-10-24 22:15:02 - Application startup complete.
INFO  : 2025-10-24 22:15:05 - Bot running. Press CTRL+C to quit.
```

- **bot.log** - события Telegram-ботов
- **webpanel.log** - события веб-панели
- **forwarder_subprocess.log** - логи подпроцесса Forwarder
- **sil_subprocess.log** - логи подпроцесса Sil_Bot
- **sil_errors.log** - ошибки бота (из error_reporter)

---

## ⚙️ Зависимости

```txt
fastapi>=0.104.0           # Web framework
uvicorn>=0.24.0            # ASGI server
python-telegram-bot>=20.0  # Telegram bot framework (Sil_Bot)
telethon>=1.28.5           # Telegram client framework (Forwarder)
python-dotenv>=1.0.0       # Environment variables
jinja2>=3.1.0              # Template engine
itsdangerous>=2.1.0        # Session security
```

---

## 🧪 Требования

- Python 3.10 или выше
- Linux/macOS/Windows
- 512 MB RAM минимум (из-за запуска нескольких подпроцессов)
- 200 MB дискового пространства

---

## 🐛 Отладка

- **Проверьте логи:** `tail -f data/logs/*.log`
- **Проверьте процессы:** Веб-панель -> вкладка "Статус"
- **Проверьте каналы:** Убедитесь, что `forwarder` подписан и имеет права на чтение.
- **Проверьте ID:** `GROUP_ID` и `CHANNELS_FILE` должны содержать корректные числовые ID.

---

## 🤝 Вклад

Мы приветствуем вклад в развитие проекта!

- Fork репозитория
- Создайте ветку (`git checkout -b feature/amazing`)
- Commit изменения (`git commit -m 'Add amazing feature'`)
- Push в ветку (`git push origin feature/amazing`)
- Откройте Pull Request

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. Подробности в файле LICENSE.

---

## ⭐ Сторонние библиотеки

- [Telethon](https://github.com/LonamiWebs/Telethon)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [FastAPI](https://github.com/tiangolo/fastapi)
- [uvicorn](https://github.com/encode/uvicorn)
