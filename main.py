from telethon import TelegramClient, events
from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# Telegram credentials
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

# Bot owner Telegram User ID
BOT_OWNER_ID = 8420696977

# Session name
SESSION_NAME = "telegram_auto_reply"

# Auto reply to the person who messages the bot
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

# Prevent duplicate processing
processed_messages = set()


@client.on(events.NewMessage(incoming=True))
async def auto_reply(event):

    # Only handle private messages
    if not event.is_private:
        return

    # Prevent duplicate processing
    if event.id in processed_messages:
        return

    processed_messages.add(event.id)

    try:
        # Get sender
        sender = await event.get_sender()

        # Name
        first_name = sender.first_name or ""
        last_name = sender.last_name or ""

        full_name = f"{first_name} {last_name}".strip()

        if not full_name:
            full_name = "N/A"

        # Username
        if sender.username:
            username = f"@{sender.username}"
        else:
            username = "No username"

        # Message
        message = event.raw_text or "(No text)"

        # ==================================================
        # PRINT USER INFORMATION IN TERMINAL
        # ==================================================

        print()
        print("=" * 60)
        print("PRIVATE MESSAGE RECEIVED")
        print("=" * 60)

        print(f"User ID  : {sender.id}")
        print(f"Name     : {full_name}")
        print(f"Username : {username}")
        print(f"Message  : {message}")

        # ==================================================
        # SEND AUTO REPLY TO USER
        # ==================================================

        await event.reply(AUTO_REPLY)

        print("Auto-reply sent successfully.")

        # ==================================================
        # SEND USER DETAILS TO BOT OWNER
        # ==================================================

        owner_message = (
            "🚨 NEW PRIVATE MESSAGE\n\n"
            f"👤 Name: {full_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 User ID: {sender.id}\n"
            f"💬 Message: {message}"
        )

        await client.send_message(
            BOT_OWNER_ID,
            owner_message
        )

        print("Owner notification sent successfully.")
        print("=" * 60)

    except Exception as e:
        print()
        print("ERROR:", e)
        print("=" * 60)


# ==========================================================
# START TELEGRAM
# ==========================================================

print("=" * 60)
print("TELEGRAM OFFLINE AUTO-REPLY")
print("=" * 60)

print("Connecting to Telegram...")

client.start()

# Get logged-in account
me = client.loop.run_until_complete(
    client.get_me()
)

print()
print(f"Logged in as: {me.first_name or 'N/A'}")

if me.username:
    print(f"Username: @{me.username}")
else:
    print("Username: No username")

print()
print("AUTO-REPLY: ACTIVE")
print("OWNER NOTIFICATION: ACTIVE")
print("Private messages: ACTIVE")

print()
print("Waiting for private messages...")
print("Press CTRL+C to stop.")
print()

# Keep running
client.run_until_disconnected()
