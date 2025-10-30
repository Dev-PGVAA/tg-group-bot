from telegram import Bot
from src.config import ADMIN_ID, BOT_TOKEN
from src.logger import logger

bot = Bot(BOT_TOKEN)

async def notify_admins(message: str):
    """Отправляет сообщение админу в личку"""
    if not ADMIN_ID:
        logger.warning("ADMIN_ID не указан, пропуск уведомления.")
        return
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=message)
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админу: {e}")
