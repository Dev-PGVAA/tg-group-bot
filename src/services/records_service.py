import json
import os
from src.config import RECORDS_FILE, REQUESTS_DIR
from src.logger import logger

os.makedirs(os.path.dirname(RECORDS_FILE), exist_ok=True)
os.makedirs(REQUESTS_DIR, exist_ok=True)

def load_records() -> dict:
    if not os.path.exists(RECORDS_FILE):
        return {}
    try:
        with open(RECORDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка при чтении {RECORDS_FILE}: {e}")
        return {}

def save_records(records: dict):
    try:
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при записи {RECORDS_FILE}: {e}")
