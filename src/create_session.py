# src/create_session.py
from telethon import TelegramClient
import config
import os

SESSION_PATH = os.path.join(os.path.dirname(__file__), "..", config.SESSION_NAME)

client = TelegramClient(SESSION_PATH, config.API_ID, config.API_HASH)

async def main():
    await client.start()
    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username})")
    print(f"Session saved to: {SESSION_PATH}.session")
    await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())