from src.logger import logger
from src.bot.error_reporter import add_error_to_queue

async def error_handler(update, context):
    err = str(context.error)
    logger.error(f"Ошибка: {err}")
    add_error_to_queue(err)
