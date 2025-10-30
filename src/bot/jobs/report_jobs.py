import os
from datetime import datetime
import src.config as config
from src.services.records_service import load_records
from src.utils.rendering import render_table_image
from src.logger import logger

REQUESTS_DIR = os.path.join(os.path.dirname(config.RECORDS_FILE), "requests")
os.makedirs(REQUESTS_DIR, exist_ok=True)

# --- Авто-отчёт каждые 14 дней ---
async def send_auto_report_job(context):
    try:
        records = load_records()
        buf = render_table_image(records)
        caption = f"📅 Авто-отчёт ({datetime.now().strftime('%Y-%m-%d')})"
        await context.bot.send_photo(
            chat_id=config.GROUP_ID,
            photo=buf,
            caption=caption,
            message_thread_id=config.TOPIC_FORWARD or None
        )
    except Exception as e:
        logger.exception("send_auto_report_job error: %s", e)
        # Ошибки не шлём сразу, они попадут в ежедневный отчёт

# --- Проверка триггера для ручных отчётов (через веб-панель) ---
async def check_trigger_and_send_report(context):
    try:
        files = [f for f in os.listdir(REQUESTS_DIR) if f.startswith("report_trigger")]
        if not files:
            return
        records = load_records()
        buf = render_table_image(records)
        caption = f"📅 Ручной отчёт ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        await context.bot.send_photo(
            chat_id=config.GROUP_ID,
            photo=buf,
            caption=caption,
            message_thread_id=config.TOPIC_FORWARD or None
        )
        for f in files:
            try:
                os.remove(os.path.join(REQUESTS_DIR, f))
            except Exception:
                pass
    except Exception as e:
        logger.exception("check_trigger_and_send_report error: %s", e)
        # Ошибки попадут в ежедневный отчёт
