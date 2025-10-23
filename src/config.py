import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# --- Telegram API ---
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

# --- Группа, куда идёт пересылка ---
GROUP_ID = int(os.getenv("GROUP_ID", "-1001234567890"))
TOPIC_FORWARD = int(os.getenv("TOPIC_FORWARD", "0"))  # ID треда (опционально)

# --- Пути к данным ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")

CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
RECORDS_FILE = os.path.join(DATA_DIR, "records.json")

# --- Логи ---
FORWARDER_LOG = os.path.join(LOGS_DIR, "bot_errors.log")
SIL_LOG = os.path.join(LOGS_DIR, "sil_errors.log")
WEBPANEL_LOG = os.path.join(LOGS_DIR, "webpanel.log")

# --- Сессия Telethon ---
SESSION_NAME = "forwarder_session"

# --- Уведомления ---
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # Куда отправлять уведомления
NOTIFIER_TOKEN = os.getenv("NOTIFIER_TOKEN", BOT_TOKEN)  # Можно использовать основной бот

# --- Настройки отчётов ---
REPORT_HOUR = int(os.getenv("REPORT_HOUR", "21"))  # Время автоотчёта DiedOnSteroidsBot
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")

# --- Веб-сервер ---
WEB_HOST = os.getenv("WEB_HOST", "localhost")
WEB_PORT = int(os.getenv("WEB_PORT", "9000"))
WEB_LOG = os.path.join(os.path.dirname(__file__), "../data/logs/webpanel.log")

# --- Создаём каталоги, если их нет ---
for path in [DATA_DIR, LOGS_DIR]:
    os.makedirs(path, exist_ok=True)
