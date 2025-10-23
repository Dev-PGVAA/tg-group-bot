# 🤖 TG Group Bot + Web Panel

**TG Group Bot** — это асинхронный Telegram-бот для управления группами с веб-панелью на FastAPI.  
Проект позволяет:

- Автоматизировать управление Telegram-группами
- Просматривать логи ботов через веб-интерфейс
- Управлять ботами через веб-панель
- Вести централизованное логирование в стиле `uvicorn`
- Легко масштабировать и расширять функционал

---

## 🚀 Основные возможности

- Управление Telegram-группами и пользователями
- Веб-панель для мониторинга и управления ботами
- Просмотр логов в реальном времени
- Асинхронная архитектура для высокой производительности
- Единый логгер с временной меткой
- Настраиваемые конфигурации через `.env` или `config.json`

---

## 🗂 Структура проекта

```

tg-group-bot/
├── src/
│ ├── main.py # Точка входа (запуск бота + webpanel)
│ ├── webpanel.py # FastAPI web-панель
│ ├── bot/ # Telegram bot
│ │ ├── handlers.py
│ │ └── ...
│ ├── logger.py # Унифицированный логгер
│ ├── static/ # Статика (css, js)
│ ├── templates/ # HTML-шаблоны
│ └── ...
├── data/ # Логи (webpanel.log, bot.log) и данные
├── venv/ # Виртуальное окружение (игнорируется)
├── requirements.txt # Зависимости
└── README.md

```

---

## ⚙️ Установка

1. Клонируем репозиторий:

```bash
git clone https://github.com/Dev-PGVAA/tg-group-bot.git
cd tg-group-bot
```

2. Создаем виртуальное окружение и активируем его:

```bash
python3 -m venv venv
source venv/bin/activate     # macOS/Linux
venv\Scripts\activate        # Windows
```

3. Устанавливаем зависимости:

```bash
pip install -r requirements.txt
```

4. Настраиваем переменные окружения через `.env` или `config.json`:

```env
TELEGRAM_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
```

---

## ▶️ Запуск

### 1. Запуск всего проекта (бот + webpanel)

```bash
python3 src/main.py
```

- Веб-панель по умолчанию доступна: `http://localhost:9000`

### 2. Запуск только webpanel

```bash
uvicorn src.webpanel:app --reload --port 9000
```

### 3. Запуск только бота

```bash
python3 src/bot/main.py
```

---

## 🧠 Логирование

Все логи оформлены в едином стиле с временной меткой:

```
INFO    : 2025-10-23 22:15:01 - Starting bot process...
INFO    : 2025-10-23 22:15:02 - Application startup complete.
INFO    : 2025-10-23 22:15:05 - Bot running. Press CTRL+C to quit.
```

- Логи сохраняются в папке `logs/`:

  - `bot.log` — события Telegram-бота
  - `webpanel.log` — события веб-панели
  - `sil_errors.log` — ошибки бота

---

## 🛠 Конфигурация

- Через `.env` или `config.json` можно задать:

  - `TELEGRAM_TOKEN` — токен бота
  - `ADMIN_ID` — Telegram ID администратора
  - `WEB_PANEL_PORT` — порт для webpanel
  - `LOG_LEVEL` — уровень логирования (`INFO`, `DEBUG`, `ERROR`)

---

## 🧰 Технологии

- Python 3.10+
- FastAPI + Uvicorn
- Aiogram (Telegram bot)
- AsyncIO
- Logging
- Jinja2 (шаблоны HTML)
- CSS / JS для веб-панели

---

## 🛠 Разработка

- Устанавливаем зависимости: `pip install -r requirements.txt`
- Запускаем с авто-перезагрузкой:

```bash
uvicorn src.webpanel:app --reload --port 9000
```

- Для изменения логирования редактируйте `src/logger.py`

---

## 📜 Лицензия

MIT © [Dev-PGVAA](https://github.com/Dev-PGVAA)
