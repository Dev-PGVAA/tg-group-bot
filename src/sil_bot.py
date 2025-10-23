import os
import io
import json
import re
import time
from logger import logger
import asyncio
from datetime import datetime, timezone, timedelta

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.error import TelegramError, NetworkError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
from utils import load_json, save_json, ensure_dir
from notifier import notify_admins

# --- Логирование ---
ensure_dir(os.path.dirname(config.SIL_LOG))

# --- Константы ---
MOVE_MAP = {
    "bench": "Жим",
    "squat": "Присед",
    "deadlift": "Тяга",
}
RECORDS_FILE = config.RECORDS_FILE

# --- Работа с записями ---
def load_records():
    return load_json(RECORDS_FILE, [])

def save_records(records):
    save_json(RECORDS_FILE, records)


# --- Безопасные отправки сообщений ---
async def delete_message_safe(bot: Bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

async def safe_reply(bot: Bot, chat_id, text, thread_id=None, **kwargs):
    try:
        if thread_id:
            return await bot.send_message(chat_id, text, message_thread_id=thread_id, **kwargs)
        return await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        log.warning("safe_reply error: %s", e)
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except Exception:
            log.exception("safe_reply final error")
            return None

async def safe_reply_photo(bot: Bot, chat_id, photo_buf, caption=None, thread_id=None, **kwargs):
    try:
        if not photo_buf:
            return None
        photo_buf.seek(0)
        if thread_id:
            return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, message_thread_id=thread_id, **kwargs)
        return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, **kwargs)
    except Exception as e:
        log.warning("safe_reply_photo error: %s", e)
        try:
            photo_buf.seek(0)
            return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, **kwargs)
        except Exception:
            log.exception("safe_reply_photo final error")
            return None


# --- Таблица (рендер в PNG) ---
def render_table_image(records):
    if not records:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.axis("off")
        ax.text(0.5, 0.5, "Нет записей", ha="center", va="center", fontsize=14)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf

    df = pd.DataFrame(records)[["user", "movement", "date", "weight"]]
    df = df.rename(columns={"user": "Имя", "movement": "Движение", "date": "Дата", "weight": "Вес (кг)"})

    fig, ax = plt.subplots(figsize=(10, max(2.5, 0.4 * len(df))))
    ax.axis("off")
    rcParams.update({'font.size': 10})
    ax.text(0.5, 1.03, "Таблица рекордов", ha='center', va='bottom', fontsize=14, fontweight='bold', transform=ax.transAxes)

    table = ax.table(cellText=df.values, colLabels=df.columns, cellLoc='center', loc='center')
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#2E86AB')
        else:
            cell.set_facecolor('#F7FAFC' if row % 2 == 0 else 'white')
        cell.set_edgecolor('#CCCCCC')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.2)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


# --- Команды ---
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
    if "bot_msgs" in context.user_data:
        for mid in context.user_data["bot_msgs"]:
            await delete_message_safe(context.bot, query.message.chat_id, mid)
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
        sent = await safe_reply(context.bot, update.message.chat_id, f"Теперь введи вес для {text} (пример: 100кг):",
                                thread_id=thread_id or config.TOPIC_FORWARD)
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]
        return

    if "movement" not in context.user_data:
        return

    m = re.search(r"(\d+[.,]?\d*)", text)
    if not m:
        await safe_reply(context.bot, update.effective_chat.id, "⚠️ Вес не распознан. Пример: 100 или 87.5",
                         thread_id=thread_id)
        return

    weight = float(m.group(1).replace(",", "."))
    weight_str = f"{weight:.2f}".rstrip("0").rstrip(".")
    movement_key = context.user_data.get("movement")
    movement_name = context.user_data.get("custom_name", "Другое") if movement_key == "custom" else MOVE_MAP.get(
        movement_key, "Другое")
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    record = {"user": username, "movement": movement_name, "weight": weight,
              "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}
    records = load_records()

    # remove old record for same user+movement
    records = [r for r in records if not (r["user"] == username and r["movement"] == movement_name)]

    best_for_move = max((r["weight"] for r in records if r["movement"] == movement_name), default=0)
    is_new_record = weight > best_for_move

    records.append(record)
    save_records(records)
    if "bot_msgs" in context.user_data:
        for mid in context.user_data["bot_msgs"]:
            await delete_message_safe(context.bot, update.message.chat_id, mid)
    context.user_data.clear()
    msg = (
        f"💥 НОВЫЙ РЕКОРД!\n{username} — {weight_str} кг в {movement_name.upper()}!"
        if is_new_record
        else f"✅ Записано: {username} — {weight_str} кг в {movement_name.upper()}"
    )
    await safe_reply(context.bot, update.message.chat_id, msg, thread_id=thread_id or config.TOPIC_FORWARD)


async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    thread_id = getattr(update.message, "message_thread_id", None)
    if not records:
        await safe_reply(context.bot, update.effective_chat.id, "Нет данных.",
                         thread_id=thread_id or config.TOPIC_FORWARD)
        return
    totals = {}
    for r in records:
        totals.setdefault(r["user"], 0)
        totals[r["user"]] += float(r["weight"])
    top_users = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = ["🏆 Топ по сумме:"] + [f"{u} — {int(s)} кг" for u, s in top_users]
    await safe_reply(context.bot, update.effective_chat.id, "\n".join(lines),
                     thread_id=thread_id or config.TOPIC_FORWARD)


async def table_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    buf = render_table_image(records)
    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply_photo(context.bot, update.effective_chat.id, buf, "📊 Таблица рекордов",
                           thread_id=thread_id or config.TOPIC_FORWARD)


# --- Авто-отчёт каждые 14 дней ---
async def send_auto_report_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        records = load_records()
        buf = render_table_image(records)
        caption = f"📅 Автоматический отчёт ({datetime.now().strftime('%Y-%m-%d')})"
        await context.bot.send_photo(chat_id=config.GROUP_ID, photo=buf, caption=caption,
                                     message_thread_id=config.TOPIC_FORWARD or None)
    except Exception as e:
        log.exception("send_auto_report_job error: %s", e)
        await notify_admins(f"Sil bot auto-report error: {e}")


# --- Проверка триггера для ручных отчётов (через веб-панель) ---
REQUESTS_DIR = os.path.join(os.path.dirname(RECORDS_FILE), "requests")
ensure_dir(REQUESTS_DIR)

async def check_trigger_and_send_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        files = [f for f in os.listdir(REQUESTS_DIR) if f.startswith("report_trigger")]
        if not files:
            return
        records = load_records()
        buf = render_table_image(records)
        caption = f"📅 Ручной отчёт ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        await context.bot.send_photo(chat_id=config.GROUP_ID, photo=buf, caption=caption,
                                     message_thread_id=config.TOPIC_FORWARD or None)
        for f in files:
            try:
                os.remove(os.path.join(REQUESTS_DIR, f))
            except Exception:
                pass
    except Exception as e:
        log.exception("check_trigger_and_send_report error: %s", e)


# --- Обработка ошибок ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("⚠️ Sil bot error: %s", context.error)
    try:
        if update and getattr(update, "message", None):
            await update.message.reply_text("⚠️ Произошла ошибка, но бот продолжает работу.")
    except Exception:
        pass
    await notify_admins(f"Sil bot error: {context.error}")


# --- Конфигурация приложения ---
def build_app():
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("sil", sil_menu))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("table", table_cmd))
    app.add_handler(CallbackQueryHandler(callback_movement))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_for_weight))
    app.add_error_handler(error_handler)

    # Планировщик: отчёт раз в 14 дней
    jq = app.job_queue
    jq.run_repeating(send_auto_report_job, interval=timedelta(days=14), first=timedelta(days=14))
    jq.run_repeating(check_trigger_and_send_report, interval=timedelta(seconds=10), first=timedelta(seconds=10))
    return app

# --- Точка входа ---
def run_polling():
    try:
        app = build_app()
        logger.info("✅ Sil bot starting polling...")
        logger.info(f"📋 Bot token: {config.BOT_TOKEN[:10]}...")
        logger.info(f"📬 Target group: {config.GROUP_ID}")
        if config.TOPIC_FORWARD:
            logger.info(f"💬 Target topic: {config.TOPIC_FORWARD}")
        
        app.run_polling(allowed_updates=None, close_loop=False)
        logger.info("Sil bot stopped.")
        
    except Exception as e:
        log.exception(f"❌ Critical error in run_polling: {e}")
        raise

if __name__ == "__main__":
    run_polling()