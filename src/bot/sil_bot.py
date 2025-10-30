import logging
from datetime import timedelta
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from src.config import BOT_TOKEN
from src.bot.handlers.help_handlers import help_cmd
from src.bot.handlers.sil_handlers import sil_menu, callback_movement, handle_text_for_weight
from src.bot.handlers.top_handlers import top_cmd, table_cmd
from src.bot.handlers.error_handler import error_handler
from src.bot.jobs.report_jobs import send_auto_report_job, check_trigger_and_send_report
from src.bot.error_reporter import start_daily_error_scheduler
from src.logger import logger

def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # --- Команды ---
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("sil", sil_menu))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("table", table_cmd))

    # --- Callback и ввод данных ---
    app.add_handler(CallbackQueryHandler(callback_movement))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_for_weight))

    # --- Обработка ошибок ---
    app.add_error_handler(error_handler)

    # --- Jobs ---
    jq = app.job_queue
    # Авто-отчёт каждые 14 дней
    jq.run_repeating(send_auto_report_job, interval=timedelta(days=14), first=timedelta(days=14))
    # Проверка ручного триггера
    jq.run_repeating(check_trigger_and_send_report, interval=10, first=10)

    # Ежедневная отправка ошибок админу
    start_daily_error_scheduler(app)

    return app


def run_polling():
    try:
        app = build_app()
        logger.info("✅ Sil bot starting polling...")
        app.run_polling(allowed_updates=None, close_loop=False)
    except Exception as e:
        logger.exception(f"❌ Critical error in run_polling: {e}")
        raise


if __name__ == "__main__":
    run_polling()