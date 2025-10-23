# src/sil_bot_main.py
import sys
from logger import logger

if __name__ == "__main__":
    try:
        logger.info("Starting Records bot...")
        from sil_bot import run_polling
        run_polling()
    except KeyboardInterrupt:
        logger.info("Records bot stopped by user")
        sys.exit(0)
    except Exception as e:
        log.exception(f"Records bot error: {e}")
        sys.exit(1)