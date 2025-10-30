from telegram import Update
from telegram.ext import ContextTypes
from src.services.records_service import load_records
from src.utils.safe_senders import safe_reply, safe_reply_photo
from src.utils.rendering import render_table_image
import src.config

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    totals = {}
    for r in records:
        totals.setdefault(r["user"], 0)
        totals[r["user"]] += float(r["weight"])
    top_users = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:10]
    lines = ["🏆 Топ по сумме:"] + [f"{u} — {int(s)} кг" for u, s in top_users]
    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply(context.bot, update.effective_chat.id, "\n".join(lines), thread_id=thread_id or config.TOPIC_FORWARD)

async def table_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    records = load_records()
    buf = render_table_image(records)
    thread_id = getattr(update.message, "message_thread_id", None)
    await safe_reply_photo(context.bot, update.effective_chat.id, buf, "📊 Таблица рекордов",
                           thread_id=thread_id or config.TOPIC_FORWARD)
