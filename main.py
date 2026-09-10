import os
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient


load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

client = TelegramClient(
    "telegram_auto_reply",
    API_ID,
    API_HASH
)


async def main():
    print("Connecting to Telegram...")

    await client.start()

    me = await client.get_me()

    print(f"Logged in as: {me.first_name}")
    print("Telegram connection successful!")


if __name__ == "__main__":
    asyncio.run(main())
