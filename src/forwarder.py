# forwarder.py
import asyncio
import json
import os
from telethon import TelegramClient, events
from telethon.errors import RPCError, ChannelPrivateError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
import config

CHANNELS_FILE = config.CHANNELS_FILE

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_channels(channels):
    with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

channels = load_channels()

client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)

@client.on(events.NewMessage(pattern=r"^/channels(?:\s.*)?$", chats=config.GROUP_ID))
async def channels_command(event):
    """
    Управление списком каналов через сообщения в GROUP_ID.
    /channels
    /channels add @username
    /channels remove @username
    """
    text = event.raw_text.strip()
    parts = text.split()
    sender = await event.get_sender()

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
                await event.reply(f"✅ Канал {chan} добавлен (возможна приватность или ошибка: {e}).")
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

@client.on(events.NewMessage)
async def forward_handler(event):
    """
    Автоматически пересылает сообщения из каналов, перечисленных в channels.json.
    Пересылает в GROUP_ID и в TOPIC_FORWARD (message_thread_id).
    Если channels.json пуст — не пересылает ничего.
    """
    try:
        if not channels:
            return

        chat = event.chat
        if chat is None:
            return
        chat_username = getattr(chat, 'username', None)
        chat_id = str(event.chat_id)

        # Normalize identifiers: strip '@' for usernames
        normalized_identifiers = [x.lstrip('@') if x.startswith('@') else x for x in channels]

        if (chat_username and chat_username.lstrip('@') in normalized_identifiers) or (chat_id in normalized_identifiers):
            try:
                # Validate TOPIC_FORWARD
                topic_id = config.TOPIC_FORWARD if hasattr(config, 'TOPIC_FORWARD') and config.TOPIC_FORWARD else None
                await client.send_message(
                    entity=config.GROUP_ID,
                    message=event.message,
                    reply_to=topic_id
                )
                print(f"[Forwarded] from {chat_id} ({chat_username}) -> group {config.GROUP_ID} thread {topic_id}")
            except TypeError as e:
                # Fallback for older Telethon versions
                try:
                    await client.send_message(
                        entity=config.GROUP_ID,
                        message=event.message
                    )
                    print(f"[Forwarded-fallback] from {chat_id} ({chat_username}) -> group {config.GROUP_ID} (no thread)")
                except Exception as e:
                    print(f"Forward error fallback: {e}")
            except RPCError as e:
                print(f"RPC error while forwarding to thread {config.TOPIC_FORWARD}: {e}")
            except Exception as e:
                print(f"Forward exception: {e}")
    except Exception as e:
        print(f"Error in forward_handler: {e}")

async def main():
    print("Запускаю Telethon forwarder...")
    await client.start()
    print("Forwarder запущен.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())