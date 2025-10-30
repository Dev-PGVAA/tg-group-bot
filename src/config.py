import os
from dotenv import load_dotenv
import pytz
from datetime import time

load_dotenv()

# === TELEGRAM ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROUP_ID = int(os.getenv("GROUP_ID", "-1000000000000"))
TOPIC_ID = int(os.getenv("TOPIC_ID", "0"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # личный ID админа, чтобы получать отчёты
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash")

# === Группа, куда идёт пересылка ===
GROUP_ID = int(os.getenv("GROUP_ID", "-1001234567890"))
TOPIC_FORWARD = int(os.getenv("TOPIC_FORWARD", "0"))  # ID треда (опционально)

# === FILES ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(DATA_DIR, "logs")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
RECORDS_FILE = os.path.join(DATA_DIR, "records.json")
RECORDS_FILE = os.path.join(DATA_DIR, "records.json")
REQUESTS_DIR = os.path.join(DATA_DIR, "requests")
SESSION_NAME = "forwarder_session"

# === LOGGING ===
BOT_LOG_FILE = os.path.join(LOG_DIR, "sil_bot.log")

# === TIME ===
MSK_TZ = pytz.timezone("Europe/Moscow")
REPORT_HOUR = 22
REPORT_MINUTE = 0
REPORT_TIME = time(REPORT_HOUR, REPORT_MINUTE, tzinfo=MSK_TZ)

# === Веб-сервер ===
WEB_HOST = os.getenv("WEB_HOST", "localhost")
WEB_PORT = int(os.getenv("WEB_PORT", "9000"))
WEB_LOG = os.path.join(os.path.dirname(__file__), "../data/logs/webpanel.log")