# src/utils.py
import json
import os
from logger import logger
from datetime import datetime

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def ensure_file(path, default):
    ensure_dir(os.path.dirname(path))
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"ensure_file write error {path}: {e}")

def load_json(path, default):
    ensure_file(path, default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"load_json error {path}: {e}")
        return default

def save_json(path, data):
    try:
        ensure_dir(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"save_json error {path}: {e}")

def record_stat(stats_path, channel):
    """
    Append a simple record for stats (date + channel).
    stats stored as list of {"date":"YYYY-MM-DD","channel":"-100... or @name"}
    """
    stats = load_json(stats_path, [])
    date = datetime.utcnow().strftime("%Y-%m-%d")
    stats.append({"date": date, "channel": channel})
    save_json(stats_path, stats)

def tail(path, lines=200):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            all_lines = f.read().splitlines()
            return all_lines[-lines:]
    except Exception as e:
        logger.error(f"tail error {path}: {e}")
        return []
