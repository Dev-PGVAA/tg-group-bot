import logging
import sys

LOG_FORMAT = "%(levelname)-8s: %(asctime)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# чтобы избежать дублирования хендлеров при повторном импорте
if not logger.hasHandlers():
    logger.addHandler(handler)
