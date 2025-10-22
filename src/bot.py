#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DiedOnSteroidsBot
Команды:
/sil — добавить рекорд (Жим / Присед / Тяга / Свое движение)
/top — топ по сумме
/table — PNG-таблица
/help — список команд
"""
import os
import io
import json
import re
import time
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
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

# -------------------- ЛОГИ --------------------
LOG_FILE = "bot_errors.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

for noisy_logger in ["httpx", "telegram", "matplotlib", "PIL"]:
    logging.getLogger(noisy_logger).setLevel(logging.ERROR)

log = logging.getLogger(__name__)

# -------------------- КОНФИГ --------------------
BOT_TOKEN = config.BOT_TOKEN
GROUP_ID = config.GROUP_ID
TOPIC_SIL = config.TOPIC_SIL
RECORDS_FILE = config.RECORDS_FILE
REPORT_INTERVAL_DAYS = config.REPORT_INTERVAL_DAYS
DATE_FORMAT = config.DATE_FORMAT

MOVE_MAP = {
    "bench": "Жим",
    "squat": "Присед",
    "deadlift": "Тяга",
}

# -------------------- Работа с файлами --------------------
def load_records():
    if os.path.exists(RECORDS_FILE):
        try:
            with open(RECORDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            log.exception("Ошибка при чтении файла записей")
            return []
    return []

def save_records(records):
    try:
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception:
        log.exception("Ошибка при сохранении файла записей")

# -------------------- Безопасные действия --------------------
async def delete_message_safe(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

async def safe_reply(bot, chat_id, text, thread_id=None, **kwargs):
    try:
        if thread_id:
            return await bot.send_message(chat_id, text, message_thread_id=thread_id, **kwargs)
        return await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        log.warning(f"Ошибка отправки сообщения: {e}")
        try:
            return await bot.send_message(chat_id, text, **kwargs)
        except Exception:
            log.exception("safe_reply: окончательная ошибка отправки")
            return None

async def safe_reply_photo(bot, chat_id, photo_buf, caption=None, thread_id=None, **kwargs):
    try:
        if not photo_buf:
            return None
        photo_buf.seek(0)
        if thread_id:
            return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, message_thread_id=thread_id, **kwargs)
        return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, **kwargs)
    except Exception as e:
        log.warning(f"Ошибка отправки фото: {e}")
        try:
            photo_buf.seek(0)
            return await bot.send_photo(chat_id, photo=photo_buf, caption=caption, **kwargs)
        except Exception:
            log.exception("safe_reply_photo: окончательная ошибка отправки фото")
            return None

# -------------------- Команды --------------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 Команды\n\n"
        "/sil — добавить рекорд (Жим / Присед / Тяга / Свое движение)\n"
        "/top — топ по сумме\n"
        "/table — таблица PNG\n"
        "/help — список команд\n\n"
        "/channels\n"
        "/channels add @username\n"
        "/channels remove @username"
    )
    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply(context.bot, update.effective_chat.id, text, thread_id=thread_id or TOPIC_SIL)

async def sil_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Жим", callback_data="bench"),
         InlineKeyboardButton("Присед", callback_data="squat")],
        [InlineKeyboardButton("Тяга", callback_data="deadlift"),
         InlineKeyboardButton("Свое движение", callback_data="custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    thread_id = getattr(update.message, "message_thread_id", None)
    sent = await safe_reply(context.bot, update.effective_chat.id, "Выбери движение 💪", thread_id=thread_id or TOPIC_SIL, reply_markup=reply_markup)
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
        sent = await safe_reply(context.bot, query.message.chat_id, "Введи название упражнения:", thread_id=thread_id or TOPIC_SIL)
        context.user_data["waiting_for_custom_name"] = True
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]
    else:
        sent = await safe_reply(context.bot, query.message.chat_id, "Введи вес в кг:", thread_id=thread_id or TOPIC_SIL)
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]

async def handle_text_for_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return  # игнорируем не-текстовые события
    text = update.message.text.strip()
    thread_id = getattr(update.message, "message_thread_id", None)
    if context.user_data.get("waiting_for_custom_name"):
        context.user_data["custom_name"] = text
        context.user_data.pop("waiting_for_custom_name")
        sent = await safe_reply(context.bot, update.message.chat_id, f"Теперь введи вес для {text} (пример: 100кг):", thread_id=thread_id or TOPIC_SIL)
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]
        return
    if "movement" not in context.user_data:
        return
    m = re.search(r"(\d+[.,]?\d*)", text)
    if not m:
        await safe_reply(context.bot, update.effective_chat.id, "⚠️ Вес не распознан. Пример: 100 или 87.5", thread_id=thread_id)
        return

    # сохраняем дробный вес
    weight = float(m.group(1).replace(",", "."))

    # аккуратный вывод (100 → "100", 87.5 → "87.5")
    weight_str = f"{weight:.2f}".rstrip("0").rstrip(".")
    movement_key = context.user_data.get("movement")
    movement_name = context.user_data.get("custom_name", "Другое") if movement_key == "custom" else MOVE_MAP.get(movement_key, "Другое")
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name
    record = {"user": username, "movement": movement_name, "weight": weight, "date": datetime.now(timezone.utc).strftime(DATE_FORMAT)}
    records = load_records()

    # Удаляем старую запись этого пользователя по тому же движению (если есть)
    records = [
        r for r in records
        if not (r["user"] == username and r["movement"] == movement_name)
    ]

    # Проверяем, побил ли он предыдущий общий рекорд по движению
    best_for_move = max((r["weight"] for r in records if r["movement"] == movement_name), default=0)
    is_new_record = weight > best_for_move

    # Добавляем новую запись
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
    await safe_reply(context.bot, update.message.chat_id, msg, thread_id=thread_id or TOPIC_SIL)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    thread_id = getattr(update.message, "message_thread_id", None)
    if not records:
        await safe_reply(context.bot, update.effective_chat.id, "Нет данных.", thread_id=thread_id or TOPIC_SIL)
        return
    totals = {}
    for r in records:
        totals.setdefault(r["user"], 0)
        totals[r["user"]] += float(r["weight"])
    top_users = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = ["🏆 Топ по сумме:"] + [f"{u} — {int(s)} кг" for u, s in top_users]
    await safe_reply(context.bot, update.effective_chat.id, "\n".join(lines), thread_id=thread_id or TOPIC_SIL)

# -------------------- Таблица PNG --------------------
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

async def table_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    buf = render_table_image(records)
    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply_photo(context.bot, update.effective_chat.id, buf, "📊 Таблица рекордов", thread_id=thread_id or TOPIC_SIL)

# -------------------- Автоотчёт --------------------
async def send_auto_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        records = load_records()
        buf = render_table_image(records)
        caption = f"📅 Автоматический отчёт ({datetime.now().strftime(DATE_FORMAT)})"
        await context.bot.send_photo(chat_id=GROUP_ID, photo=buf, caption=caption, message_thread_id=TOPIC_SIL)
    except Exception as e:
        log.exception(f"Ошибка автоотчёта: {e}")

# -------------------- Обработчик ошибок --------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("⚠️ Ошибка: %s", context.error)
    try:
        if update and getattr(update, "message", None):
            await update.message.reply_text("⚠️ Произошла ошибка, но бот продолжает работу.")
    except Exception:
        pass

# -------------------- Запуск --------------------
def main():
    while True:
        try:
            app = ApplicationBuilder().token(BOT_TOKEN).build()
            app.add_handler(CommandHandler("help", help_cmd))
            app.add_handler(CommandHandler("sil", sil_menu))
            app.add_handler(CommandHandler("top", top_cmd))
            app.add_handler(CommandHandler("table", table_cmd))
            app.add_handler(CallbackQueryHandler(callback_movement))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_for_weight))
            app.add_error_handler(error_handler)
            job_queue = app.job_queue
            job_queue.run_repeating(send_auto_report, interval=timedelta(days=REPORT_INTERVAL_DAYS), first=timedelta(seconds=10))
            log.info("✅ Бот запущен")
            app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)
        except TelegramError as e:
            if "Conflict" in str(e):
                log.warning("⚠️ Обнаружен конфликт polling — перезапуск через 5 сек.")
                time.sleep(5)
                continue
            else:
                log.exception("TelegramError: %s", e)
                time.sleep(10)
        except NetworkError:
            log.warning("Сетевой сбой — повтор через 5 сек.")
            time.sleep(5)
        except Exception as e:
            log.exception("Неожиданная ошибка: %s", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
    