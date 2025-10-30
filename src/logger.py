import logging
from logging.handlers import RotatingFileHandler
from src.config import BOT_LOG_FILE
import os

os.makedirs(os.path.dirname(BOT_LOG_FILE), exist_ok=True)

logger = logging.getLogger("sil_bot")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(BOT_LOG_FILE, maxBytes=2_000_000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
