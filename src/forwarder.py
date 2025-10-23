# src/forwarder.py
import asyncio
from logger import logger
import time
import os
from telethon import TelegramClient, events
from telethon.errors import RPCError, FloodWaitError, ChannelPrivateError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
import config
from utils import load_json, save_json, record_stat
from notifier import notify_admins

logger = logger.getLogger("forwarder")

# Session file path
SESSION_PATH = os.path.join(os.path.dirname(__file__), "..", config.SESSION_NAME)
logger.info(f"Using session file: {SESSION_PATH}")

# Load channels
channels = []

def reload_channels():
    global channels
    channels = load_json(config.CHANNELS_FILE, [])
    logger.info(f"Loaded {len(channels)} channels: {channels}")
    return channels

# Initial load
reload_channels()

client = TelegramClient(SESSION_PATH, config.API_ID, config.API_HASH)

_last_forward_time = 0

def set_last_forward_time(ts=None):
    global _last_forward_time
    _last_forward_time = ts or int(time.time())

def get_last_forward_time():
    return _last_forward_time

async def try_join_channel(chan):
    try:
        entity = await client.get_entity(chan)
        try:
            await client(JoinChannelRequest(entity))
            logger.info(f"✅ Joined channel {chan}")
        except UserAlreadyParticipantError:
            logger.info(f"Already participant in {chan}")
        except ChannelPrivateError:
            logger.warning(f"⚠️ Channel {chan} is private (can't join)")
    except Exception as e:
        logger.warning(f"❌ Failed to get/join entity {chan}: {e}")

@client.on(events.NewMessage(pattern=r"^/channels(?:\s.*)?$", chats=config.GROUP_ID))
async def channels_command(event):
    try:
        text = event.raw_text.strip()
        parts = text.split()
        
        if len(parts) == 1:
            # List channels
            reload_channels()
            if channels:
                await event.reply("📋 **Отслеживаемые каналы:**\n" + "\n".join(f"• {ch}" for ch in channels))
            else:
                await event.reply("📋 Список каналов пуст.\n\nДобавьте канал: /channels add @username")
            return
            
        cmd = parts[1].lower()
        
        if cmd == "add" and len(parts) >= 3:
            chan = parts[2]
            reload_channels()
            if chan not in channels:
                channels.append(chan)
                save_json(config.CHANNELS_FILE, channels)
                await try_join_channel(chan)
                await event.reply(f"✅ Канал {chan} добавлен в список отслеживания.")
                logger.info(f"Added channel: {chan}")
            else:
                await event.reply(f"⚠️ Канал {chan} уже в списке.")
                
        elif cmd == "remove" and len(parts) >= 3:
            chan = parts[2]
            reload_channels()
            if chan in channels:
                channels.remove(chan)
                save_json(config.CHANNELS_FILE, channels)
                await event.reply(f"❌ Канал {chan} удалён из списка отслеживания.")
                logger.info(f"Removed channel: {chan}")
            else:
                await event.reply(f"⚠️ Канал {chan} не найден в списке.")
                
        else:
            await event.reply(
                "**Управление каналами:**\n\n"
                "📋 Показать список:\n`/channels`\n\n"
                "➕ Добавить канал:\n`/channels add @username`\n\n"
                "➖ Удалить канал:\n`/channels remove @username`"
            )
            
    except Exception as e:
        logger.exception(f"channels_command error: {e}")
        await event.reply(f"❌ Ошибка: {e}")

@client.on(events.NewMessage(incoming=True))
async def forward_handler(event):
    try:
        # Reload channels periodically (every 100 messages or so)
        if not hasattr(forward_handler, '_counter'):
            forward_handler._counter = 0
        forward_handler._counter += 1
        if forward_handler._counter % 100 == 0:
            reload_channels()
        
        # Skip if no channels
        if not channels:
            return
        
        # Skip own messages
        if event.out:
            return
            
        # Get chat info
        chat = event.chat
        if not chat:
            return
            
        chat_username = getattr(chat, "username", None)
        chat_id = str(event.chat_id)
        
        # Normalize channel names (remove @)
        normalized_channels = []
        for ch in channels:
            if isinstance(ch, str):
                normalized_channels.append(ch.lstrip("@"))
            else:
                normalized_channels.append(str(ch))
        
        # Check if message is from tracked channel
        should_forward = False
        matched_channel = None
        
        # Check by username
        if chat_username:
            username_clean = chat_username.lstrip("@")
            if username_clean in normalized_channels:
                should_forward = True
                matched_channel = chat_username
        
        # Check by ID
        if not should_forward and chat_id in normalized_channels:
            should_forward = True
            matched_channel = chat_id
        
        # Also check original format with @
        if not should_forward and chat_username:
            if f"@{chat_username}" in channels or chat_username in channels:
                should_forward = True
                matched_channel = chat_username
        
        if should_forward:
            try:
                logger.info(f"📨 Forwarding message from {matched_channel} (chat_id: {chat_id})")
                
                # Try to forward with topic support
                try:
                    if config.TOPIC_FORWARD:
                        await client.send_message(
                            entity=config.GROUP_ID,
                            message=event.message,
                            reply_to=config.TOPIC_FORWARD
                        )
                    else:
                        await client.send_message(
                            entity=config.GROUP_ID,
                            message=event.message
                        )
                except TypeError:
                    # Fallback without reply_to
                    await client.send_message(
                        entity=config.GROUP_ID,
                        message=event.message
                    )
                
                # Record stats
                record_stat(config.STATS_FILE, matched_channel)
                set_last_forward_time()
                
                logger.info(f"✅ Successfully forwarded from {matched_channel}")
                
            except FloodWaitError as e:
                logger.warning(f"⏳ FloodWait: need to wait {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
                # Retry after wait
                try:
                    await client.send_message(entity=config.GROUP_ID, message=event.message)
                    logger.info(f"✅ Forwarded after FloodWait from {matched_channel}")
                except Exception as retry_error:
                    logger.error(f"❌ Failed to forward after FloodWait: {retry_error}")
                    
            except RPCError as e:
                logger.error(f"❌ RPCError while forwarding: {e}")
                await notify_admins(f"⚠️ Forwarder RPCError: {e}")
                
            except Exception as e:
                logger.error(f"❌ Error forwarding message: {e}")
                await notify_admins(f"⚠️ Forwarder error: {e}")
                
    except Exception as e:
        logger.exception(f"❌ forward_handler critical error: {e}")

async def run_forwarder():
    # Check session file exists
    session_file = f"{SESSION_PATH}.session"
    if not os.path.exists(session_file):
        logger.error(f"❌ Session file not found: {session_file}")
        logger.error("Please run: python src/create_session.py")
        raise FileNotFoundError(f"Session file not found: {session_file}")
    
    logger.info(f"✅ Session file found: {session_file}")
    
    while True:
        try:
            logger.info("🚀 Starting forwarder...")
            
            await client.start()
            
            # Check authorization
            me = await client.get_me()
            logger.info(f"✅ Logged in as: {me.first_name} (@{me.username})")
            
            # Reload channels
            reload_channels()
            logger.info(f"📋 Tracking {len(channels)} channels")
            
            # Join all channels
            if channels:
                logger.info("🔗 Joining channels...")
                for ch in channels:
                    await try_join_channel(ch)
                    await asyncio.sleep(1)  # Small delay between joins
                logger.info("✅ Channel joining complete")
            else:
                logger.warning("⚠️ No channels configured! Add channels with: /channels add @username")
            
            logger.info("✅ Forwarder is now running and listening for messages...")
            logger.info(f"📬 Messages will be forwarded to GROUP_ID: {config.GROUP_ID}")
            if config.TOPIC_FORWARD:
                logger.info(f"💬 Using topic ID: {config.TOPIC_FORWARD}")
            
            await client.run_until_disconnected()
            
        except (OSError, ConnectionError, asyncio.TimeoutError) as e:
            logger.warning(f"⚠️ Connection lost: {e}. Reconnecting in 10s...")
            await notify_admins(f"⚠️ Forwarder connection lost: {e}")
            await asyncio.sleep(10)
            
        except Exception as e:
            logger.exception(f"❌ Critical forwarder error: {e}")
            await notify_admins(f"🚨 Forwarder critical error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_forwarder())