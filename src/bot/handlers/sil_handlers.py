import re
from datetime import datetime, timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from src.services.records_service import load_records, save_records
from src.utils.safe_senders import safe_reply
from src.logger import logger
import src.config

MOVE_MAP = {
    "bench": "Жим",
    "squat": "Присед",
    "deadlift": "Тяга",
}

async def sil_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Жим", callback_data="bench"),
         InlineKeyboardButton("Присед", callback_data="squat")],
        [InlineKeyboardButton("Тяга", callback_data="deadlift"),
         InlineKeyboardButton("Свое движение", callback_data="custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    thread_id = getattr(update.message, "message_thread_id", None)
    sent = await safe_reply(context.bot, update.effective_chat.id, "Выбери движение 💪",
                            thread_id=thread_id or config.TOPIC_FORWARD, reply_markup=reply_markup)
    if sent:
        context.user_data["bot_msgs"] = [sent.message_id]

async def callback_movement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    context.user_data["movement"] = data

    for mid in context.user_data.get("bot_msgs", []):
        try:
            await context.bot.delete_message(query.message.chat_id, mid)
        except Exception:
            pass

    thread_id = getattr(query.message, "message_thread_id", None)
    if data == "custom":
        sent = await safe_reply(context.bot, query.message.chat_id, "Введи название упражнения:",
                                thread_id=thread_id or config.TOPIC_FORWARD)
        context.user_data["waiting_for_custom_name"] = True
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]
    else:
        sent = await safe_reply(context.bot, query.message.chat_id, "Введи вес в кг:",
                                thread_id=thread_id or config.TOPIC_FORWARD)
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]

async def handle_text_for_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    thread_id = getattr(update.message, "message_thread_id", None)

    if context.user_data.get("waiting_for_custom_name"):
        context.user_data["custom_name"] = text
        context.user_data.pop("waiting_for_custom_name")
        sent = await safe_reply(context.bot, update.message.chat_id,
                                f"Теперь введи вес для {text} (пример: 100кг):",
                                thread_id=thread_id or config.TOPIC_FORWARD)
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]
        return

    if "movement" not in context.user_data:
        return

    m = re.search(r"(\d+[.,]?\d*)", text)
    if not m:
        await safe_reply(context.bot, update.effective_chat.id,
                         "⚠️ Вес не распознан. Пример: 100 или 87.5",
                         thread_id=thread_id)
        return

    weight = float(m.group(1).replace(",", "."))
    movement_key = context.user_data.get("movement")
    movement_name = context.user_data.get("custom_name", "Другое") if movement_key == "custom" else MOVE_MAP.get(movement_key, "Другое")
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    record = {
        "user": username, 
        "movement": movement_name, 
        "weight": weight,
        "date": datetime.now().strftime("%d.%m.%Y")
    }
    records = load_records()
    records = [r for r in records if not (r["user"] == username and r["movement"] == movement_name)]
    records.append(record)
    save_records(records)

    for mid in context.user_data.get("bot_msgs", []):
        try:
            await context.bot.delete_message(update.message.chat_id, mid)
        except Exception:
            pass
    context.user_data.clear()

    msg = f"✅ Записано: {username} — {weight} кг в {movement_name.upper()}"
    await safe_reply(context.bot, update.message.chat_id, msg, thread_id=thread_id or config.TOPIC_FORWARD)
