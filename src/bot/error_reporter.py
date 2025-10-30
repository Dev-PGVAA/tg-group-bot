import asyncio
from datetime import datetime
from telegram.ext import Application
from src.config import REPORT_TIME, ADMIN_ID, MSK_TZ
from src.logger import logger

_error_queue = []

def add_error_to_queue(err: str):
    _error_queue.append(f"[{datetime.now(MSK_TZ).strftime('%Y-%m-%d %H:%M:%S')}] {err}")

async def send_daily_error_report(app: Application):
    if not _error_queue:
        logger.info("Нет ошибок для отчёта.")
        return
    text = "📋 Ежедневный отчёт об ошибках:\n\n" + "\n".join(_error_queue[-50:])
    _error_queue.clear()
    try:
        await app.bot.send_message(chat_id=ADMIN_ID, text=text)
        logger.info("Отчёт об ошибках отправлен админу.")
    except Exception as e:
        logger.error(f"Не удалось отправить отчёт админу: {e}")

def start_daily_error_scheduler(app: Application):
    app.job_queue.run_daily(send_daily_error_report, time=REPORT_TIME, name="daily_error_report")
