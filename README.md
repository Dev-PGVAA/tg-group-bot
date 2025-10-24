# 🤖 TG Group Bot

> Асинхронный Telegram-бот для управления группами с веб-панелью на FastAPI

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-orange.svg)](https://aiogram.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Возможности

- 🔐 **Защищенная веб-панель** с системой авторизации
- 📊 **Мониторинг в реальном времени** - статус бота, логи, uptime
- 🤖 **Управление Telegram-группами** - автоматизация и модерация
- 📝 **Централизованное логирование** в стиле uvicorn
- ⚡ **Асинхронная архитектура** для высокой производительности
- 🎯 **Модульная структура** - легко расширять функционал
- 🚀 **Фоновый запуск** с автоматическим управлением
- 💾 **Гибкая конфигурация** через `.env` или `config.json`

## 📂 Структура проекта

```
tg-group-bot/
├── src/
│   ├── main.py              # Точка входа (бот + webpanel)
│   ├── webpanel.py          # 🔐 FastAPI панель с авторизацией
│   ├── logger.py            # Унифицированный логгер
│   ├── bot/                 # Telegram бот
│   │   ├── handlers.py      # Обработчики команд
│   │   └── ...
│   ├── templates/           # HTML-шаблоны для веб-панели
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── logs.html
│   │   └── settings.html
│   └── static/              # Статические файлы (CSS, JS)
├── data/
│   ├── logs/                # Логи всех компонентов
│   │   ├── bot.log          # Логи Telegram бота
│   │   ├── webpanel.log     # Логи веб-панели
│   │   └── sil_errors.log   # Ошибки бота
│   ├── pids/                # PID файлы процессов
│   └── users.json           # Данные пользователей (авторизация)
├── venv/                    # Виртуальное окружение
├── bot_manager.py           # 🚀 Скрипт управления ботом
├── requirements.txt         # Python зависимости
├── .env                     # Конфигурация (создайте из примера)
└── README.md
```

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/Dev-PGVAA/tg-group-bot.git
cd tg-group-bot
```

### 2. Создание виртуального окружения

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации

Создайте файл `.env` или `config.json`:

**Вариант 1: .env файл** (рекомендуется)

```bash
# Telegram Bot
TELEGRAM_TOKEN=your_bot_token_from_botfather
ADMIN_ID=your_telegram_id

# Web Panel
WEB_PANEL_PORT=9000
WEB_PANEL_HOST=0.0.0.0
SECRET_KEY=your_random_secret_key_32_chars_minimum

# Logging
LOG_LEVEL=INFO
```

**Вариант 2: config.json**

```json
{
	"telegram": {
		"token": "your_bot_token",
		"admin_id": "your_telegram_id"
	},
	"webpanel": {
		"port": 9000,
		"host": "0.0.0.0",
		"secret_key": "your_secret_key"
	},
	"logging": {
		"level": "INFO"
	}
}
```

### 5. Запуск проекта

**Способ 1: Через менеджер (рекомендуется)**

```bash
# Запуск в фоновом режиме
python3 bot_manager.py start

# Проверка статуса
python3 bot_manager.py status

# Просмотр логов
python3 bot_manager.py logs

# Остановка
python3 bot_manager.py stop

# Перезапуск
python3 bot_manager.py restart
```

**Способ 2: Прямой запуск**

```bash
python3 src/main.py
```

**Способ 3: Только веб-панель**

```bash
python3 src/webpanel.py
# или
uvicorn src.webpanel:app --reload --port 9000
```

**Способ 4: Только бот**

```bash
python3 src/bot/main.py
```

### 6. Доступ к веб-панели

Откройте браузер: **http://localhost:9000**

**Данные для входа по умолчанию:**

```
Логин: admin
Пароль: admin123
```

⚠️ **ВАЖНО: Сразу смените пароль через "Настройки"!**

## 🔐 Безопасность

### Смена пароля

1. Войдите в веб-панель
2. Перейдите в "Настройки"
3. Введите текущий и новый пароль
4. После смены войдите заново

### Добавление пользователя

```python
import json
import hashlib
from pathlib import Path

username = "newuser"
password = "secure_password"

users_file = Path("data/users.json")
with open(users_file, 'r') as f:
    users = json.load(f)

users[username] = {
    "password": hashlib.sha256(password.encode()).hexdigest(),
    "created_at": "2025-10-24T12:00:00",
    "role": "user"
}

with open(users_file, 'w') as f:
    json.dump(users, f, indent=2)
```

### Генерация SECRET_KEY

```python
import secrets
print(secrets.token_hex(32))
```

## 📊 Логирование

Все логи сохраняются в папке `data/logs/` в едином стиле:

```
INFO  : 2025-10-24 22:15:01 - Starting bot process...
INFO  : 2025-10-24 22:15:02 - Application startup complete.
INFO  : 2025-10-24 22:15:05 - Bot running. Press CTRL+C to quit.
```

### Типы логов

- **bot.log** - события Telegram-бота
- **webpanel.log** - события веб-панели
- **sil_errors.log** - ошибки бота

### Просмотр логов

```bash
# Через менеджер
python3 bot_manager.py logs

# Напрямую
tail -f data/logs/bot.log
tail -f data/logs/webpanel.log

# В веб-панели
# Откройте страницу "Логи" в браузере
```

## 🛠️ Управление ботом

### Bot Manager (Рекомендуется)

```bash
python3 bot_manager.py <команда>

Команды:
  start    - Запустить бота в фоновом режиме
  stop     - Остановить бота
  restart  - Перезапустить бота
  status   - Проверить статус (PID, память)
  logs     - Показать последние логи
  help     - Показать справку
```

### Systemd Service (Автозапуск)

Для автоматического запуска при загрузке сервера:

```bash
# 1. Отредактируйте tg-bot.service
nano tg-bot.service

# 2. Скопируйте в systemd
sudo cp tg-bot.service /etc/systemd/system/

# 3. Включите автозапуск
sudo systemctl daemon-reload
sudo systemctl enable tg-bot
sudo systemctl start tg-bot

# 4. Проверка
sudo systemctl status tg-bot
```

### Screen (Альтернатива)

```bash
# Запуск в screen
screen -dmS tgbot python3 src/main.py

# Подключение к сессии
screen -r tgbot

# Отключение (не останавливая): Ctrl+A, затем D

# Остановка
screen -S tgbot -X quit
```

## 🌐 Веб-панель

### Доступные страницы

- **/** - Главная панель (статус бота, uptime, PID)
- **/logs** - Просмотр логов в реальном времени
- **/settings** - Настройки пользователя, смена пароля
- **/login** - Страница входа
- **/logout** - Выход из системы

### API Endpoints

```
GET  /api/status              - Статус бота (JSON)
GET  /api/logs?log_type=bot   - Логи (JSON)
POST /api/change-password     - Смена пароля
```

Все API требуют авторизации через сессию.

## 🔧 Конфигурация

### Переменные окружения (.env)

```bash
# Telegram
TELEGRAM_TOKEN=             # Токен от @BotFather
ADMIN_ID=                   # Ваш Telegram ID

# Web Panel
WEB_PANEL_PORT=9000         # Порт веб-панели
WEB_PANEL_HOST=0.0.0.0      # Хост (0.0.0.0 для внешнего доступа)
SECRET_KEY=                 # Ключ для сессий (32+ символов)

# Logging
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
```

### Получение Telegram ID

1. Напишите боту [@userinfobot](https://t.me/userinfobot)
2. Или используйте [@getmyid_bot](https://t.me/getmyid_bot)

## 📦 Зависимости

### Python Packages

```
fastapi>=0.104.0           # Web framework
uvicorn>=0.24.0            # ASGI server
aiogram>=3.0.0             # Telegram bot framework
python-dotenv>=1.0.0       # Environment variables
jinja2>=3.1.0              # Template engine
itsdangerous>=2.1.0        # Session security
```

### Системные требования

- Python 3.10 или выше
- Linux/macOS/Windows
- 256 MB RAM минимум
- 100 MB дискового пространства

## 🐛 Решение проблем

### Бот не запускается

```bash
# Проверьте токен
cat .env | grep TELEGRAM_TOKEN

# Проверьте логи
tail -f data/logs/bot.log

# Проверьте процесс
python3 bot_manager.py status
```

### Веб-панель не открывается

```bash
# Проверьте порт
lsof -i :9000

# Проверьте логи
tail -f data/logs/webpanel.log

# Измените порт
echo "WEB_PANEL_PORT=8080" >> .env
```

### Ошибка авторизации

```bash
# Пересоздайте пользователей
rm data/users.json
python3 src/webpanel.py

# Проверьте файл
cat data/users.json
```

### Логи не отображаются

```bash
# Проверьте права
ls -la data/logs/
chmod 644 data/logs/*.log

# Проверьте наличие
ls data/logs/bot.log
```

## 📝 Разработка

### Структура логгера

`src/logger.py` предоставляет унифицированное логирование:

```python
from src.logger import get_logger

logger = get_logger(__name__)

logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")
```

### Добавление обработчиков бота

```python
# src/bot/handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Я бот для управления группами.")
```

### Расширение веб-панели

```python
# src/webpanel.py
from fastapi import Depends

@app.get("/api/custom")
async def custom_endpoint(user: str = Depends(require_auth)):
    return {"message": "Custom API endpoint"}
```

## 🚀 Деплой в продакшн

### Настройка HTTPS через Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd сервис

```ini
[Unit]
Description=Telegram Group Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/tg-group-bot
Environment="PATH=/path/to/tg-group-bot/venv/bin"
ExecStart=/path/to/tg-group-bot/venv/bin/python3 /path/to/tg-group-bot/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker (опционально)

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python3", "src/main.py"]
```

## 📖 Документация API

После запуска веб-панели документация доступна:

- Swagger UI: http://localhost:9000/docs
- ReDoc: http://localhost:9000/redoc

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта!

1. Fork репозитория
2. Создайте ветку (`git checkout -b feature/amazing`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в ветку (`git push origin feature/amazing`)
5. Откройте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. Подробности в файле [LICENSE](LICENSE).

## 👤 Автор

**Dev-PGVAA**

- GitHub: [@Dev-PGVAA](https://github.com/Dev-PGVAA)
- Project Link: [tg-group-bot](https://github.com/Dev-PGVAA/tg-group-bot)

## 🙏 Благодарности

- [FastAPI](https://fastapi.tiangolo.com/) - веб-фреймворк
- [Aiogram](https://aiogram.dev/) - Telegram Bot framework
- [Uvicorn](https://www.uvicorn.org/) - ASGI сервер

---

⭐ Если проект был полезен, поставьте звезду на GitHub!
