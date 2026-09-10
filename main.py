import os
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient, events


# Load .env
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not API_ID or not API_HASH:
    raise ValueError("API_ID or API_HASH is missing from .env")

API_ID = int(API_ID)


# Telegram client
client = TelegramClient(
    "telegram_auto_reply",
    API_ID,
    API_HASH
)


# Auto-reply message
AUTO_REPLY = "TEST AUTO REPLY"


# Processed messages
processed_messages = set()


# Incoming private messages
@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):

    if not event.message.text:
        return

    if not event.is_private:
        return

    sender = await event.get_sender()

    if sender is None:
        return

    message_id = event.message.id

    if message_id in processed_messages:
        return

    processed_messages.add(message_id)

    message = event.message.text.strip()

    print()
    print("=" * 50)
    print("PRIVATE MESSAGE RECEIVED")
    print("=" * 50)
    print(f"From: {sender.first_name}")
    print(f"Message: {message}")

    try:
        await event.reply(AUTO_REPLY)
        print("Auto-reply sent successfully.")

    except Exception as error:
        print("ERROR:", error)

    print("=" * 50)


# Main
async def main():

    print("=" * 50)
    print("TELEGRAM OFFLINE AUTO-REPLY")
    print("=" * 50)

    print("Connecting to Telegram...")

    await client.start()

    me = await client.get_me()

    print()
    print(f"Logged in as: {me.first_name}")

    if me.username:
        print(f"Username: @{me.username}")

    print()
    print("AUTO-REPLY: ACTIVE")
    print("Private messages: ACTIVE")
    print()
    print("Waiting for private messages...")
    print("Press CTRL+C to stop.")
    print()

    await client.run_until_disconnected()


# Start
if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nAuto-reply stopped.")
