import asyncio
import json
import os
import logging
from telethon import TelegramClient, events
from telethon.errors import (
    RPCError,
    ChannelPrivateError,
    UserAlreadyParticipantError,
    FloodWaitError,
    ConnectionError as TelethonConnectionError,
)
from telethon.tl.functions.channels import JoinChannelRequest
import config

# --- Логирование ---
logging.basicConfig(
    filename="bot_errors.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

CHANNELS_FILE = config.CHANNELS_FILE


# --- Работа с файлами каналов ---
def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.warning("⚠️ Ошибка чтения JSON каналов. Файл повреждён.")
                return []
    return []


def save_channels(channels):
    try:
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump(channels, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"❌ Не удалось сохранить список каналов: {e}")


channels = load_channels()

client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)


# --- Команда /channels ---
@client.on(events.NewMessage(pattern=r"^/channels(?:\s.*)?$", chats=config.GROUP_ID))
async def channels_command(event):
    try:
        text = event.raw_text.strip()
        parts = text.split()

        if len(parts) == 1:
            if channels:
                await event.reply("📋 Список каналов для пересылки:\n" + "\n".join(channels))
            else:
                await event.reply("Список каналов пуст. Добавь через `/channels add @username`.")
            return

        cmd = parts[1].lower()
        if cmd == "add" and len(parts) >= 3:
            chan = parts[2]
            if chan not in channels:
                try:
                    entity = await client.get_entity(chan)
                    try:
                        await client(JoinChannelRequest(entity))
                    except (ChannelPrivateError, UserAlreadyParticipantError):
                        pass
                    channels.append(chan)
                    save_channels(channels)
                    await event.reply(f"✅ Канал {chan} добавлен в пересылку.")
                except Exception as e:
                    channels.append(chan)
                    save_channels(channels)
                    await event.reply(f"✅ Канал {chan} добавлен (ошибка при join: {e}).")
                    logging.warning(f"Ошибка при добавлении канала {chan}: {e}")
            else:
                await event.reply("Этот канал уже в списке.")
        elif cmd == "remove" and len(parts) >= 3:
            chan = parts[2]
            if chan in channels:
                channels.remove(chan)
                save_channels(channels)
                await event.reply(f"❌ Канал {chan} удалён из пересылки.")
            else:
                await event.reply("Такого канала нет в списке.")
        else:
            await event.reply("Неверная команда. Используй `/channels add @username` или `/channels remove @username`.")
    except Exception as e:
        logging.error(f"Ошибка в channels_command: {e}")


# --- Пересылка сообщений ---
@client.on(events.NewMessage)
async def forward_handler(event):
    try:
        if not channels:
            return

        chat = event.chat
        if chat is None:
            return
        chat_username = getattr(chat, "username", None)
        chat_id = str(event.chat_id)

        normalized_identifiers = [x.lstrip("@") if x.startswith("@") else x for x in channels]

        if (chat_username and chat_username.lstrip("@") in normalized_identifiers) or (chat_id in normalized_identifiers):
            topic_id = getattr(config, "TOPIC_FORWARD", None)

            try:
                await client.send_message(
                    entity=config.GROUP_ID,
                    message=event.message,
                    reply_to=topic_id
                )
                logging.info(f"[Forwarded] from {chat_id} ({chat_username}) -> group {config.GROUP_ID} thread {topic_id}")
            except TypeError:
                # fallback без thread
                await client.send_message(entity=config.GROUP_ID, message=event.message)
                logging.info(f"[Forwarded-fallback] from {chat_id} ({chat_username}) -> group {config.GROUP_ID} (no thread)")
            except FloodWaitError as e:
                logging.warning(f"FloodWait на {e.seconds} сек. Пауза...")
                await asyncio.sleep(e.seconds)
            except RPCError as e:
                logging.error(f"RPC error while forwarding: {e}")
            except Exception as e:
                logging.error(f"Ошибка пересылки: {e}")

    except Exception as e:
        logging.error(f"Ошибка в forward_handler: {e}")


# --- Основной цикл ---
async def run_client():
    while True:
        try:
            logging.info("🚀 Запуск Telethon forwarder...")
            await client.start()
            logging.info("✅ Forwarder запущен.")
            await client.run_until_disconnected()
        except TelethonConnectionError as e:
            logging.warning(f"🔁 Потеря соединения: {e}. Перезапуск через 10 сек...")
            await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"❌ Критическая ошибка в клиенте: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_client())
