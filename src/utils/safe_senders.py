from telegram import Bot
from src.logger import logger

async def safe_reply(bot: Bot, chat_id, text: str, thread_id=None, **kwargs):
    """
    Безопасная отправка текста. Если thread_id указан — отправка в тред.
    """
    try:
        if thread_id:
            return await bot.send_message(chat_id, text, message_thread_id=thread_id, **kwargs)
        return await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logger.warning("safe_reply error: %s", e)
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except Exception:
            logger.exception("safe_reply final error")
            return None

async def safe_reply_photo(bot: Bot, chat_id, photo_buf, caption=None, thread_id=None, **kwargs):
    """
    Безопасная отправка фото. Если thread_id указан — отправка в тред.
    """
    if not photo_buf:
        return None
    try:
        photo_buf.seek(0)
        if thread_id:
            return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, message_thread_id=thread_id, **kwargs)
        return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, **kwargs)
    except Exception as e:
        logger.warning("safe_reply_photo error: %s", e)
        try:
            photo_buf.seek(0)
            return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, **kwargs)
        except Exception:
            logger.exception("safe_reply_photo final error")
            return None
