from telegram import Update
from telegram.ext import ContextTypes
from src.utils.safe_senders import safe_reply
import src.config

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
			"📋 Команды\n\n" 
			"/sil — добавить рекорд (Жим / Присед / Тяга / Свое движение)\n" 
			"/top — топ по сумме\n"
			"/table — таблица PNG\n" 
			"/help — список команд\n\n" 
			"Forwarder команды:\n" 
			"/channels add @username\n" 
			"/channels remove @username"
    )
    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply(context.bot, update.effective_chat.id, text, thread_id=thread_id or config.TOPIC_FORWARD)
 