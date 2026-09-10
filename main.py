import os
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient, events


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not API_ID:
    raise ValueError("API_ID is missing from your .env file")

if not API_HASH:
    raise ValueError("API_HASH is missing from your .env file")

API_ID = int(API_ID)


# ============================================================
# TELEGRAM CLIENT
# ============================================================

client = TelegramClient(
    "telegram_auto_reply",
    API_ID,
    API_HASH
)


# ============================================================
# AUTO REPLY MESSAGE
# ============================================================

AUTO_REPLY = """
Hello! 👋

The owner is currently offline.

Please wait for some time. He will get back to you as soon as possible.

Thank you for your patience! 😊
""".strip()


# ============================================================
# PROCESSED MESSAGES
# ============================================================

processed_messages = set()


# ============================================================
# HANDLE PRIVATE MESSAGES
# ============================================================

@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):

    # Ignore messages without text
    if not event.message.text:
        return

    # Only private messages
    if not event.is_private:
        return

    # Get sender
    sender = await event.get_sender()

    if sender is None:
        return

    # Prevent duplicate replies
    message_id = event.message.id

    if message_id in processed_messages:
        return

    processed_messages.add(message_id)

    # Incoming message
    message = event.message.text.strip()

    print()
    print("=" * 60)
    print("PRIVATE MESSAGE RECEIVED")
    print("=" * 60)

    print(f"From: {sender.first_name}")
    print(f"Message: {message}")

    try:

        # Send offline auto-reply
        await event.reply(AUTO_REPLY)

        print("Auto-reply sent successfully.")

    except Exception as error:

        print("ERROR:", error)

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 60)
    print("TELEGRAM OFFLINE AUTO-REPLY")
    print("=" * 60)

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


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nAuto-reply stopped.")
