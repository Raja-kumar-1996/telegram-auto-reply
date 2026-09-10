import os
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient, events


# Load environment variables from .env
load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not API_ID or not API_HASH:
    raise ValueError(
        "API_ID and API_HASH are missing from your .env file"
    )

API_ID = int(API_ID)


# Create Telegram client
client = TelegramClient(
    "telegram_auto_reply",
    API_ID,
    API_HASH
)


# Keep track of processed messages
processed_messages = set()


@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):

    # Ignore messages without text
    if not event.message.text:
        return

    # Only handle private chats
    if not event.is_private:
        return

    # Get sender
    sender = await event.get_sender()

    # Ignore unknown/service messages
    if sender is None:
        return

    # Get message ID
    message_id = event.message.id

    # Prevent duplicate processing
    if message_id in processed_messages:
        return

    processed_messages.add(message_id)

    # Get incoming message
    incoming_message = event.message.text.strip()

    print("\n" + "=" * 50)
    print("New message received")
    print("=" * 50)

    print(f"User: {sender.first_name}")
    print(f"Message: {incoming_message}")

    # ------------------------------------------------
    # Temporary reply
    # ------------------------------------------------
    reply = "Hello! 👋 I received your message."

    # Send reply
    await event.reply(reply)

    print(f"Reply: {reply}")
    print("=" * 50)


async def main():

    print("=" * 50)
    print("Telegram Auto Reply Bot")
    print("=" * 50)

    print("Connecting to Telegram...")

    await client.start()

    me = await client.get_me()

    print()
    print(f"Logged in as: {me.first_name}")

    if me.username:
        print(f"Username: @{me.username}")

    print()
    print("Auto-reply is ACTIVE")
    print("Waiting for private messages...")
    print("Press CTRL+C to stop.")
    print()

    # Keep program running
    await client.run_until_disconnected()


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nBot stopped.")
