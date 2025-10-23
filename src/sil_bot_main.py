# src/sil_bot_main.py
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("sil_bot_main")

if __name__ == "__main__":
    try:
        log.info("Starting DiedOnSteroids bot...")
        from sil_bot import run_polling
        run_polling()
    except KeyboardInterrupt:
        log.info("DiedOnSteroids bot stopped by user")
        sys.exit(0)
    except Exception as e:
        log.exception(f"DiedOnSteroids bot error: {e}")
        sys.exit(1)