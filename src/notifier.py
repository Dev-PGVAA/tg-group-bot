# src/notifier.py
import urllib.request
import urllib.parse
import json
import logging
import config

# Simple notifier using Telegram Bot HTTP API (no extra deps).
# It posts messages to ADMIN_CHAT_ID via bot token.

def _bot_api(method, params=None, files=None):
    """
    Minimal wrapper for Telegram Bot API.
    For simple text messages we'll use JSON-encoded body.
    """
    token = config.BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None
    headers = {}
    if params is not None:
        data = json.dumps(params).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logging.error(f"Notifier _bot_api error: {e}")
        return None

def notify_text(chat_id, text):
    try:
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        return _bot_api("sendMessage", params=params)
    except Exception as e:
        logging.error(f"notify_text error: {e}")
        return None

def notify_admins(text):
    """
    Send text to ADMIN_CHAT_ID if configured (or to GROUP_ID fallback).
    """
    target = config.ADMIN_CHAT_ID or config.GROUP_ID
    if not target:
        logging.warning("notify_admins: no ADMIN_CHAT_ID or GROUP_ID configured")
        return
    return notify_text(target, text)
