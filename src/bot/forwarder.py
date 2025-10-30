import asyncio
import os
from telethon import TelegramClient, events
from telethon.errors import RPCError, FloodWaitError, ChannelPrivateError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest

from src.config import API_ID, API_HASH, SESSION_NAME, GROUP_ID, TOPIC_FORWARD, CHANNELS_FILE, STATS_FILE
from src.utils.utils import load_json, save_json, record_stat
from src.logger import logger
from src.bot.error_reporter import add_error_to_queue

# --- Session ---
SESSION_PATH = os.path.join(os.path.dirname(__file__), SESSION_NAME)
client = TelegramClient(SESSION_PATH, API_ID, API_HASH)

# --- Channels ---
channels = []
monitored_entities = []  # Список entity для мониторинга

def reload_channels():
    global channels
    channels = load_json(CHANNELS_FILE, [])
    logger.info(f"Loaded {len(channels)} channels: {channels}")
    return channels

reload_channels()

# --- Join channel helper ---
async def try_join_channel(chan):
    try:
        entity = await client.get_entity(chan)
        try:
            await client(JoinChannelRequest(entity))
            logger.info(f"✅ Joined channel {chan}")
        except UserAlreadyParticipantError:
            logger.info(f"Already participant in {chan}")
        except ChannelPrivateError:
            logger.warning(f"⚠️ Channel {chan} is private")
        return entity
    except Exception as e:
        logger.warning(f"❌ Failed to join {chan}: {e}")
        add_error_to_queue(str(e))
        return None

# --- Update monitored channels ---
async def update_monitored_channels():
    """Обновляет список отслеживаемых каналов"""
    global monitored_entities
    monitored_entities = []
    
    reload_channels()
    if not channels:
        logger.warning("No channels to monitor")
        return
    
    logger.info(f"🔄 Updating monitored channels: {channels}")
    
    for chan in channels:
        try:
            entity = await client.get_entity(chan)
            monitored_entities.append(entity.id)
            logger.info(f"✓ Monitoring: {chan} (ID: {entity.id})")
        except Exception as e:
            logger.warning(f"❌ Cannot get entity for {chan}: {e}")
    
    logger.info(f"📡 Total monitored entities: {len(monitored_entities)} - IDs: {monitored_entities}")

# --- Command handler ---
@client.on(events.NewMessage(pattern=r"^/channels(?:\s.*)?$", chats=GROUP_ID))
async def channels_command(event):
    try:
        text = event.raw_text.strip()
        parts = text.split()
        
        if len(parts) == 1:
            reload_channels()
            if channels:
                await event.reply("📋 Отслеживаемые каналы:\n" + "\n".join(f"• {ch}" for ch in channels))
            else:
                await event.reply("📋 Список каналов пуст. Добавьте канал: /channels add @username")
            return

        cmd = parts[1].lower()
        if cmd == "add" and len(parts) >= 3:
            chan = parts[2]
            reload_channels()
            if chan not in channels:
                channels.append(chan)
                save_json(CHANNELS_FILE, channels)
                entity = await try_join_channel(chan)
                # Обновляем список мониторинга
                await update_monitored_channels()
                await event.reply(f"✅ Канал {chan} добавлен и мониторится")
            else:
                await event.reply(f"⚠️ Канал {chan} уже есть")
        elif cmd == "remove" and len(parts) >= 3:
            chan = parts[2]
            reload_channels()
            if chan in channels:
                channels.remove(chan)
                save_json(CHANNELS_FILE, channels)
                # Обновляем список мониторинга
                await update_monitored_channels()
                await event.reply(f"❌ Канал {chan} удалён")
            else:
                await event.reply(f"⚠️ Канал {chan} не найден")
        else:
            await event.reply(
                "**Управление каналами:**\n"
                "/channels — показать список\n"
                "/channels add @username — добавить\n"
                "/channels remove @username — удалить"
            )
    except Exception as e:
        logger.exception(f"channels_command error: {e}")
        add_error_to_queue(str(e))

# --- Forward handler ---
@client.on(events.NewMessage(incoming=True))
async def forward_handler(event):
    try:
        if not hasattr(forward_handler, '_counter'):
            forward_handler._counter = 0
        forward_handler._counter += 1
        
        # Периодическое обновление списка каналов
        if forward_handler._counter % 100 == 0:
            await update_monitored_channels()

        if event.out:
            return

        # ВАЖНО: Игнорируем сообщения из целевой группы (избегаем цикла)
        if event.chat_id == GROUP_ID or str(event.chat_id) == str(GROUP_ID):
            return

        # Проверяем, что канал в списке мониторинга
        if event.chat_id not in monitored_entities:
            return

        chat = event.chat
        if not chat:
            return
        
        chat_username = getattr(chat, "username", None)
        chat_id = str(event.chat_id)
        chat_title = getattr(chat, "title", None)

        # Определяем matched_channel для статистики
        matched_channel = None
        if chat_username:
            matched_channel = f"@{chat_username}"
        elif chat_title:
            matched_channel = chat_title
        else:
            matched_channel = chat_id

        logger.info(f"🔄 Forwarding from {matched_channel} (ID: {event.chat_id})")
        
        try:
            # Получаем текст оригинального сообщения
            original_text = event.message.text or ""
            
            # Формируем подпись канала
            if chat_username:
                channel_link = f"@{chat_username}"
            elif chat_title:
                channel_link = chat_title
            else:
                channel_link = f"ID: {chat_id}"
            
            footer = f"\n\n📢 Переслано из канала: {channel_link}"
            
            # Если это медиа, пересылаем с подписью
            if event.message.media:
                new_caption = (event.message.text or "") + footer
                kwargs = {
                    "entity": GROUP_ID,
                    "file": event.message.media,
                    "message": new_caption,
                    "silent": True
                }
                if TOPIC_FORWARD:
                    kwargs["reply_to"] = TOPIC_FORWARD
                await client.send_file(**kwargs)
            else:
                # Если это текстовое сообщение
                new_text = original_text + footer
                kwargs = {
                    "entity": GROUP_ID,
                    "message": new_text,
                    "silent": True
                }
                if TOPIC_FORWARD:
                    kwargs["reply_to"] = TOPIC_FORWARD
                await client.send_message(**kwargs)
            
            record_stat(STATS_FILE, matched_channel)
            logger.info(f"✅ Forwarded from {matched_channel} (silent)")
            
        except FloodWaitError as e:
            logger.warning(f"⏳ FloodWait {e.seconds}s")
            add_error_to_queue(f"Forwarder FloodWait {e.seconds}s: {matched_channel}")
            await asyncio.sleep(e.seconds)
            
        except RPCError as e:
            logger.error(f"RPCError forwarding from {matched_channel}: {e}")
            add_error_to_queue(f"Forwarder RPCError: {e}")
        except Exception as e:
            logger.exception(f"Forwarding error from {matched_channel}: {e}")
            add_error_to_queue(str(e))
                
    except Exception as e:
        logger.exception(f"Critical forward_handler error: {e}")
        add_error_to_queue(str(e))

# --- Run forwarder ---
async def run_forwarder():
    session_file = f"{SESSION_PATH}.session"
    if not os.path.exists(session_file):
        logger.error(f"Session file not found: {session_file}")
        raise FileNotFoundError(f"Session file not found: {session_file}")

    while True:
        try:
            await client.start()
            me = await client.get_me()
            logger.info(f"✅ Logged in as: {me.first_name} (@{me.username})")
            
            # Загружаем и подписываемся на все каналы
            reload_channels()
            if channels:
                logger.info(f"📡 Joining {len(channels)} channels...")
                for ch in channels:
                    await try_join_channel(ch)
                    await asyncio.sleep(1)
            
            # Обновляем список мониторинга
            await update_monitored_channels()
            
            logger.info("🚀 Forwarder running...")
            logger.info(f"👀 Watching {len(monitored_entities)} channels")
            await client.run_until_disconnected()
        except (OSError, ConnectionError, asyncio.TimeoutError) as e:
            logger.warning(f"Connection lost: {e}. Reconnecting in 10s...")
            add_error_to_queue(str(e))
            await asyncio.sleep(10)
        except Exception as e:
            logger.exception(f"Critical forwarder error: {e}")
            add_error_to_queue(str(e))
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_forwarder())