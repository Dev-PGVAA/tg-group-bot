from telegram.ext import ContextTypes
from src.bot.error_reporter import add_error_to_queue
import logging

logger = logging.getLogger(__name__)

MAX_ERROR_LEN = 1000  # максимальная длина строки ошибки в очереди

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок: логируем и добавляем в очередь для ежедневного отчёта."""
    err = context.error
    try:
        # Формируем текст ошибки с информацией об апдейте
        update_info = ""
        if update:
            chat_id = getattr(getattr(update, "effective_chat", None), "id", None)
            user_id = getattr(getattr(update, "effective_user", None), "id", None)
            update_info = f"[chat_id={chat_id} user_id={user_id}] "

        error_text = f"{update_info}{str(err)}"
        if len(error_text) > MAX_ERROR_LEN:
            error_text = error_text[:MAX_ERROR_LEN] + " ... [truncated]"

        # Логируем локально
        logger.exception("⚠️ Sil bot error: %s", err)

        # Добавляем в очередь для ежедневного отчёта админу
        add_error_to_queue(error_text)

    except Exception as e:
        # Если сам обработчик упал — хотя бы залогируем
        logger.exception("❌ Exception in error_handler: %s", e)
