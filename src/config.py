# config.py
import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8226360976:AAGm0jeLtH3UikusTWbMzBlgeSHR0EQmL1Y")

# Common group / supergroup chat id where bot operates
GROUP_ID = int(os.getenv("GROUP_ID", 1002511221161))

# Topic/thread id where strength bot reacts (число топика)
TOPIC_SIL = int(os.getenv("TOPIC_SIL", 5762))

# Telethon userbot settings for forwarder
API_ID = int(os.getenv("API_ID", "21309518") or 21309518)
API_HASH = os.getenv("API_HASH", "a3adb5b639768800cb1db4a59ff10281")
SESSION_NAME = os.getenv("SESSION_NAME", "forwarder")

# Topic/thread id for forwarder (пересылка)
TOPIC_FORWARD = int(os.getenv("TOPIC_FORWARD", 5761))

# Files
RECORDS_FILE = os.getenv("RECORDS_FILE", "records.json")
CHANNELS_FILE = os.getenv("CHANNELS_FILE", "channels.json")

# Template
CONGRATS_TEMPLATE = "💥 НОВЫЙ РЕКОРД!\n{user} — {kg} кг в {movement}!"

# Report interval
REPORT_INTERVAL_DAYS = int(os.getenv("REPORT_INTERVAL_DAYS", "14"))

DATE_FORMAT = "%d-%m-%Y"
