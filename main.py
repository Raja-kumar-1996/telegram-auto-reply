from telethon import TelegramClient, events
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Telegram credentials
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Session name
SESSION_NAME = "telegram_auto_reply"

# Auto reply message
AUTO_REPLY = (
    "Hey! 👋 Thanks for messaging me.\n\n"
    "I'm currently away and may not be able to reply right now. "
    "Please leave me a message and I'll get back to you as soon as possible.\n\n"
    "Thanks for understanding! 😊"
)

# Create Telegram client
client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH
)

# Keep track of processed messages
processed_messages = set()


@client.on(events.NewMessage(incoming=True))
async def auto_reply(event):

    # Only respond to private messages
    if not event.is_private:
        return

    # Avoid processing the same message twice
    if event.id in processed_messages:
        return

    processed_messages.add(event.id)

    try:
        # Get sender information
        sender = await event.get_sender()

        # Get name
        first_name = sender.first_name or ""
        last_name = sender.last_name or ""

        full_name = f"{first_name} {last_name}".strip()

        if not full_name:
            full_name = "N/A"

        # Get username
        username = sender.username

        # Get message text
        message = event.raw_text

        # Print information in terminal
        print()
        print("=" * 60)
        print("PRIVATE MESSAGE RECEIVED")
        print("=" * 60)

        print(f"User ID  : {sender.id}")
        print(f"Name     : {full_name}")

        if username:
            print(f"Username : @{username}")
        else:
            print("Username : No username")

        print(f"Message  : {message}")

        # Send auto reply
        await event.reply(AUTO_REPLY)

        print("Auto-reply sent successfully.")
        print("=" * 60)

    except Exception as e:
        print()
        print("ERROR:", e)
        print("=" * 60)


# Start Telegram client
print("=" * 60)
print("TELEGRAM OFFLINE AUTO-REPLY")
print("=" * 60)

print("Connecting to Telegram...")

client.start()

# Show logged-in account
me = client.loop.run_until_complete(client.get_me())

print()
print(f"Logged in as: {me.first_name or 'N/A'}")

if me.username:
    print(f"Username: @{me.username}")
else:
    print("Username: No username")

print()
print("AUTO-REPLY: ACTIVE")
print("Private messages: ACTIVE")
print()
print("Waiting for private messages...")
print("Press CTRL+C to stop.")
print()

# Keep program running
client.run_until_disconnected()
