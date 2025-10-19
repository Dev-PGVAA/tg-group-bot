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
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rcParams
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Импорт настроек из config.py
# config.py должен содержать: BOT_TOKEN, GROUP_ID, TOPIC_SIL (опционально), REPORT_INTERVAL_DAYS (опционально), RECORDS_FILE (опционально), DATE_FORMAT (опционально)
import config

LOG_FILE = "bot_errors.log"

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()  # Удали эту строку, если не хочешь видеть логи в консоли
    ]
)

# Отключаем лишние логи сторонних библиотек
for noisy_logger in ["httpx", "telegram", "matplotlib", "PIL"]:
    logging.getLogger(noisy_logger).setLevel(logging.ERROR)

log = logging.getLogger(__name__)

# -------------------- КОНФИГ --------------------
BOT_TOKEN = getattr(config, "BOT_TOKEN", None)
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in config.py")

RECORDS_FILE = getattr(config, "RECORDS_FILE", "records.json")
TOPIC_SIL = int(getattr(config, "TOPIC_SIL", 0)) if getattr(config, "TOPIC_SIL", None) is not None else 0
GROUP_ID = int(getattr(config, "GROUP_ID", 0)) if getattr(config, "GROUP_ID", None) is not None else 0
REPORT_INTERVAL_DAYS = int(getattr(config, "REPORT_INTERVAL_DAYS", 14))
DATE_FORMAT = getattr(config, "DATE_FORMAT", "%d-%m-%Y")

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
            log.exception("Не удалось прочитать файл записей, возвращаю пустой список")
            return []
    return []

def save_records(records):
    try:
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception:
        log.exception("Не удалось сохранить файл записей")

# -------------------- Утилиты безопасной отправки/удаления --------------------
async def delete_message_safe(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        # игнорируем ошибки удаления
        pass

async def safe_reply(bot, chat_id, text, thread_id=None, **kwargs):
    try:
        if thread_id:
            return await bot.send_message(chat_id=chat_id, text=text, message_thread_id=thread_id, **kwargs)
        else:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
    except Exception as e:
        log.warning("safe_reply: ошибка при отправке в thread_id=%s: %s. Попытка отправить без thread_id.", thread_id, e)
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except Exception:
            log.exception("safe_reply: окончательная ошибка отправки сообщения")
            raise

async def safe_reply_photo(bot, chat_id, photo_buf, caption=None, thread_id=None, **kwargs):
    try:
        # Проверим, что буфер не пустой
        if photo_buf is None:
            log.warning("safe_reply_photo: передан None вместо BytesIO — отмена отправки")
            return None
        # Если это file-like — постараемся проверить размер
        try:
            nbytes = photo_buf.getbuffer().nbytes
        except Exception:
            nbytes = None
        if nbytes == 0:
            log.warning("safe_reply_photo: буфер пуст (0 байт) — отмена отправки")
            return None
        photo_buf.seek(0)
        if thread_id:
            return await bot.send_photo(chat_id=chat_id, photo=photo_buf, caption=caption, message_thread_id=thread_id, **kwargs)
        else:
            return await bot.send_photo(chat_id=chat_id, photo=photo_buf, caption=caption, **kwargs)
    except Exception as e:
        log.warning("safe_reply_photo: ошибка при отправке в thread_id=%s: %s. Попытка отправить без thread_id.", thread_id, e)
        try:
            photo_buf.seek(0)
            return await bot.send_photo(chat_id=chat_id, photo=photo_buf, caption=caption, **kwargs)
        except Exception:
            log.exception("safe_reply_photo: окончательная ошибка отправки фото")
            raise

# -------------------- Команды --------------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 Команды\n\n"
        "/sil — добавить рекорд (Жим / Присед / Тяга / Свое движение)\n"
        "/top — топ по сумме\n"
        "/table — таблица PNG\n"
        "/help — список команд\n"
        "/channels\n"
        "/channels add @username\n"
        "/channels remove @username"
    )
    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply(context.bot, update.effective_chat.id, text, thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))

async def sil_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Жим", callback_data="bench"),
         InlineKeyboardButton("Присед", callback_data="squat")],
        [InlineKeyboardButton("Тяга", callback_data="deadlift"),
         InlineKeyboardButton("Свое движение", callback_data="custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    thread_id = getattr(update.message, "message_thread_id", None)
    sent = await safe_reply(context.bot, update.effective_chat.id, "Выбери движение 💪", thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None), reply_markup=reply_markup)
    # Сохраняем id бота-сообщения, чтобы потом удалять его (диалог)
    if sent:
        context.user_data["bot_msgs"] = [sent.message_id]

async def callback_movement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    context.user_data["movement"] = data

    # удаляем старое сообщение меню, если было
    if "bot_msgs" in context.user_data:
        for mid in context.user_data["bot_msgs"]:
            await delete_message_safe(context.bot, query.message.chat_id, mid)

    thread_id = getattr(query.message, "message_thread_id", None)

    if data == "custom":
        sent = await safe_reply(context.bot, query.message.chat_id, "Введи название своего упражнения (например: Армейский жим):", thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))
        context.user_data["waiting_for_custom_name"] = True
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]
    else:
        sent = await safe_reply(context.bot, query.message.chat_id, "Введи вес в кг (пример: 100 или 100кг):", thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]

async def handle_text_for_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    thread_id = getattr(update.message, "message_thread_id", None)

    # если ждем название кастомного движения
    if context.user_data.get("waiting_for_custom_name"):
        context.user_data["custom_name"] = text
        context.user_data.pop("waiting_for_custom_name")
        sent = await safe_reply(context.bot, update.message.chat_id, f"Теперь введи вес для {text} (пример: 100 или 100кг):", thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))
        if sent:
            context.user_data["bot_msgs"] = [sent.message_id]
        return

    if "movement" not in context.user_data:
        # нет контекста движения — игнорируем
        return

    # Парсим вес
    m = re.search(r"(\d+[.,]?\d*)", text)
    if not m:
        await safe_reply(context.bot, update.effective_chat.id, "⚠️ Вес не распознан. Пример: 100", thread_id=thread_id)
        return
    try:
        weight = int(float(m.group(1).replace(",", ".")))
    except Exception:
        await safe_reply(context.bot, update.effective_chat.id, "⚠️ Ошибка формата веса. Пример: 100", thread_id=thread_id)
        return

    movement_key = context.user_data.get("movement")
    if movement_key == "custom":
        movement_name = context.user_data.get("custom_name", "Другое")
    else:
        movement_name = MOVE_MAP.get(movement_key, "Другое")

    user = update.effective_user
    username = f"@{user.username}" if user.username else user.full_name

    record = {
        "user": username,
        "movement": movement_name,
        "weight": weight,
        "date": datetime.now(timezone.utc).strftime(DATE_FORMAT),
    }

    records = load_records()
    best_for_move = max((r["weight"] for r in records if r["movement"] == movement_name), default=0)
    is_new_record = weight > best_for_move
    records.append(record)
    save_records(records)

    # очистка диалога
    if "bot_msgs" in context.user_data:
        for mid in context.user_data["bot_msgs"]:
            await delete_message_safe(context.bot, update.message.chat_id, mid)
    context.user_data.clear()

    if is_new_record:
        msg = f"💥 НОВЫЙ РЕКОРД!\n{username} — {weight} кг в {movement_name.upper()}!"
    else:
        msg = f"✅ Записано: {username} — {weight} кг в {movement_name.upper()}"

    await safe_reply(context.bot, update.message.chat_id, msg, thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    thread_id = getattr(update.message, "message_thread_id", None)

    if not records:
        await safe_reply(context.bot, update.effective_chat.id, "Нет данных.", thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))
        return
    totals = {}
    for r in records:
        totals.setdefault(r["user"], 0)
        totals[r["user"]] += float(r["weight"])
    top_users = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = ["🏆 Топ по сумме:"]
    for u, s in top_users:
        lines.append(f"{u} — {int(s)} кг")
    await safe_reply(context.bot, update.effective_chat.id, "\n".join(lines), thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))

# -------------------- Таблица PNG --------------------
def render_table_image(records):
    # Возврат BytesIO с PNG
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

    # защита от пустого буфера
    try:
        size = buf.getbuffer().nbytes
    except Exception:
        size = None
    if size == 0:
        log.warning("table_cmd: сформированный буфер пуст — отмена отправки")
        await safe_reply(context.bot, update.effective_chat.id, "Не удалось сформировать таблицу (пустой файл).", thread_id=getattr(update.message, "message_thread_id", None) or (TOPIC_SIL if TOPIC_SIL else None))
        return

    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply_photo(context.bot, update.effective_chat.id, buf, "📊 Таблица рекордов", thread_id=thread_id or (TOPIC_SIL if TOPIC_SIL else None))

# -------------------- Автоматический отчёт --------------------
async def send_auto_report(context: ContextTypes.DEFAULT_TYPE):
    try:
        records = load_records()
        buf = render_table_image(records)

        try:
            size = buf.getbuffer().nbytes
        except Exception:
            size = None
        if size == 0:
            log.warning("send_auto_report: сформированный буфер пуст — пропускаем отправку")
            return

        buf.seek(0)
        caption = f"📅 Автоматический отчёт ({datetime.now().strftime(DATE_FORMAT)})"
        # Пытаемся отправить в TOPIC_SIL если он задан, иначе просто в GROUP_ID
        if TOPIC_SIL:
            await context.bot.send_photo(chat_id=GROUP_ID, photo=buf, caption=caption, message_thread_id=TOPIC_SIL)
        else:
            await context.bot.send_photo(chat_id=GROUP_ID, photo=buf, caption=caption)
        log.info("Автоотчёт отправлен")
    except Exception as e:
        log.exception("Ошибка при отправке автоотчёта: %s", e)

# -------------------- Запуск --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Хэндлеры
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("sil", sil_menu))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("table", table_cmd))
    app.add_handler(CallbackQueryHandler(callback_movement))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_for_weight))

    # Автоотчёт через job_queue (в фоне)
    job_queue = app.job_queue
    job_queue.run_repeating(send_auto_report, interval=timedelta(days=REPORT_INTERVAL_DAYS), first=timedelta(seconds=10))

    log.info("✅ Died on steroids bot - запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
