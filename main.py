import os
import asyncio

from dotenv import load_dotenv
from telethon import TelegramClient, events
from openai import OpenAI


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not API_ID:
    raise ValueError("API_ID is missing from your .env file")

if not API_HASH:
    raise ValueError("API_HASH is missing from your .env file")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is missing from your .env file")

API_ID = int(API_ID)


# ============================================================
# OPENAI
# ============================================================

ai = OpenAI(
    api_key=OPENAI_API_KEY
)


# ============================================================
# TELEGRAM
# ============================================================

client = TelegramClient(
    "telegram_auto_reply",
    API_ID,
    API_HASH
)


# ============================================================
# CONVERSATION MEMORY
# ============================================================

conversation_history = {}


# ============================================================
# PROCESSED MESSAGE IDs
# ============================================================

processed_messages = set()


# ============================================================
# GENERATE AI REPLY
# ============================================================

def generate_reply(chat_id, user_message):

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # Add user message
    conversation_history[chat_id].append({
        "role": "user",
        "content": user_message
    })

    # Keep recent conversation only
    conversation_history[chat_id] = (
        conversation_history[chat_id][-20:]
    )

    instructions = """
You are a friendly personal Telegram assistant.

Reply naturally and conversationally.

Rules:

1. Understand the language used by the user.
2. Normally reply in the same language.
3. If the user mixes languages, respond naturally in the same style.
4. Keep normal replies reasonably short.
5. Give detailed answers when the user asks for details.
6. Do not mention that you are an AI unless the user asks.
7. Do not say that you are a Telegram bot.
8. Be friendly, polite and helpful.
9. Do not unnecessarily repeat the user's message.
"""

    response = ai.responses.create(
        model="gpt-5.6-luna",
        instructions=instructions,
        input=conversation_history[chat_id],
        max_output_tokens=500
    )

    reply = response.output_text.strip()

    # Save AI reply
    conversation_history[chat_id].append({
        "role": "assistant",
        "content": reply
    })

    # Keep memory limited
    conversation_history[chat_id] = (
        conversation_history[chat_id][-20:]
    )

    return reply


# ============================================================
# HANDLE NEW TELEGRAM MESSAGE
# ============================================================

@client.on(events.NewMessage(incoming=True))
async def handle_new_message(event):

    # Ignore messages without text
    if not event.message.text:
        return

    # Only private chats
    if not event.is_private:
        return

    # Get sender
    sender = await event.get_sender()

    if sender is None:
        return

    # Message ID
    message_id = event.message.id

    # Prevent duplicate processing
    if message_id in processed_messages:
        return

    processed_messages.add(message_id)

    # Get message
    incoming_message = event.message.text.strip()

    if not incoming_message:
        return

    print()
    print("=" * 60)
    print("NEW MESSAGE")
    print("=" * 60)

    print(f"User: {sender.first_name}")
    print(f"Message: {incoming_message}")

    try:

        # Generate AI response
        reply = await asyncio.to_thread(
            generate_reply,
            event.chat_id,
            incoming_message
        )

        print(f"AI Reply: {reply}")

        # Send AI reply
        await event.reply(reply)

        print("Reply sent successfully.")

    except Exception as error:

        print("ERROR:", error)

        try:
            await event.reply(
                "Sorry, I couldn't generate a reply right now."
            )
        except Exception:
            pass

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 60)
    print("AI TELEGRAM AUTO-REPLY")
    print("=" * 60)

    print("Connecting to Telegram...")

    await client.start()

    me = await client.get_me()

    print()
    print(f"Logged in as: {me.first_name}")

    if me.username:
        print(f"Username: @{me.username}")

    print()
    print("AI AUTO-REPLY: ACTIVE")
    print("OpenAI: ACTIVE")
    print("Multilingual replies: ACTIVE")
    print("Private chats: ACTIVE")
    print("Conversation memory: ACTIVE")
    print()
    print("Waiting for messages...")
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
        print("\nBot stopped.")
