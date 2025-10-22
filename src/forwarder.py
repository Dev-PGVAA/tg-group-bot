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
)
from telethon.tl.functions.channels import JoinChannelRequest
import config

# --- ЛОГИРОВАНИЕ ---
logging.basicConfig(
    filename="bot_errors.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

CHANNELS_FILE = config.CHANNELS_FILE


# --- ЗАГРУЗКА / СОХРАНЕНИЕ КАНАЛОВ ---
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


# --- /channels КОМАНДЫ ---
@client.on(events.NewMessage(pattern=r"^/channels(?:\s.*)?$", chats=config.GROUP_ID))
async def channels_command(event):
    try:
        text = event.raw_text.strip()
        parts = text.split()

        if len(parts) == 1:
            if channels:
                msg = "📋 **Список каналов для пересылки:**\n" + "\n".join(channels)
            else:
                msg = "Список каналов пуст. Добавь через `/channels add @username` или ID."
            await event.reply(msg)
            return

        cmd = parts[1].lower()
        if cmd == "add" and len(parts) >= 3:
            chan = parts[2]
            if chan not in channels:
                try:
                    entity = await client.get_entity(chan)
                    try:
                        await client(JoinChannelRequest(entity))
                        logging.info(f"✅ Присоединился к каналу {chan}")
                    except UserAlreadyParticipantError:
                        logging.info(f"ℹ️ Уже в канале {chan}")
                    except ChannelPrivateError:
                        logging.warning(f"⚠️ Канал {chan} приватный, пригласи аккаунт вручную.")
                    channels.append(chan)
                    save_channels(channels)
                    await event.reply(f"✅ Канал {chan} добавлен в пересылку.")
                except Exception as e:
                    channels.append(chan)
                    save_channels(channels)
                    await event.reply(f"⚠️ Канал {chan} добавлен, но не удалось получить entity: {e}")
                    logging.error(f"Ошибка при добавлении {chan}: {e}")
            else:
                await event.reply("Этот канал уже в списке.")
        elif cmd == "remove" and len(parts) >= 3:
            chan = parts[2]
            if chan in channels:
                channels.remove(chan)
                save_channels(channels)
                await event.reply(f"❌ Канал {chan} удалён.")
            else:
                await event.reply("Такого канала нет в списке.")
        else:
            await event.reply("Используй `/channels add @username` или `/channels remove @username`.")
    except Exception as e:
        logging.error(f"Ошибка в channels_command: {e}")


# --- АНТИ-ДУБЛИКАТ ---
last_forwarded = set()


# --- ОСНОВНАЯ ПЕРЕСЫЛКА ---
@client.on(events.NewMessage(incoming=True))
async def forward_handler(event):
    try:
        if not channels:
            return

        chat = event.chat
        if not chat:
            return

        chat_username = getattr(chat, "username", None)
        chat_id = str(event.chat_id)
        normalized = [x.lstrip("@") if x.startswith("@") else x for x in channels]

        if chat_id not in normalized and (not chat_username or chat_username.lstrip("@") not in normalized):
            return  # не из нужного канала

        # проверка на дубли
        if event.id in last_forwarded:
            return
        last_forwarded.add(event.id)
        if len(last_forwarded) > 2000:
            last_forwarded.clear()

        topic_id = getattr(config, "TOPIC_FORWARD", None)

        try:
            await client.send_message(
                entity=config.GROUP_ID,
                message=event.message,
                reply_to=topic_id
            )
            logging.info(f"[Forwarded] {chat_id} ({chat_username}) -> group {config.GROUP_ID} thread {topic_id}")
        except TypeError:
            await client.send_message(entity=config.GROUP_ID, message=event.message)
            logging.info(f"[Fallback] {chat_id} ({chat_username}) -> group {config.GROUP_ID}")
        except FloodWaitError as e:
            logging.warning(f"⏳ FloodWait на {e.seconds} сек, пауза...")
            await asyncio.sleep(e.seconds)
        except RPCError as e:
            logging.error(f"RPC ошибка при пересылке: {e}")
        except Exception as e:
            logging.error(f"Ошибка при пересылке: {e}")

    except Exception as e:
        logging.error(f"Ошибка в forward_handler: {e}")


# --- ОТЛАДОЧНЫЙ ЛОГ ---
@client.on(events.NewMessage)
async def debug_handler(event):
    try:
        chat = event.chat
        chat_id = getattr(chat, "id", None)
        username = getattr(chat, "username", None)
        if chat_id and username:
            logging.debug(f"[DEBUG] Сообщение из {chat_id} ({username}): {event.raw_text[:50]}")
    except Exception:
        pass


# --- ЦИКЛ ПЕРЕЗАПУСКА ---
async def run_client():
    while True:
        try:
            logging.info("🚀 Запуск Telethon forwarder...")
            await client.start()
            logging.info("✅ Forwarder запущен.")
            await client.run_until_disconnected()
        except (OSError, asyncio.TimeoutError, ConnectionError) as e:
            logging.warning(f"🔁 Потеря соединения: {e}, перезапуск через 10 сек...")
            await asyncio.sleep(10)
        except Exception as e:
            logging.error(f"❌ Критическая ошибка клиента: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(run_client())