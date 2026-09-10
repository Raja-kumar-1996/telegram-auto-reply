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
# OPENAI CLIENT
# ============================================================

ai = OpenAI(
    api_key=OPENAI_API_KEY
)


# ============================================================
# TELEGRAM CLIENT
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
# PROCESSED MESSAGE TRACKING
# ============================================================

processed_messages = set()


# ============================================================
# AI RESPONSE FUNCTION
# ============================================================

def generate_reply(chat_id, user_message):

    # Create conversation history for this chat
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # Add user's message
    conversation_history[chat_id].append({
        "role": "user",
        "content": user_message
    })

    # Keep only recent messages
    conversation_history[chat_id] = (
        conversation_history[chat_id][-20:]
    )

    # System instructions
    instructions = """
You are a friendly personal Telegram assistant.

Reply naturally and conversationally.

Important rules:

1. Understand the language used by the user.
2. Normally reply in the same language.
3. If the user mixes languages, respond naturally using the same style.
4. Keep normal replies reasonably short.
5. Give detailed answers when the user asks for details.
6. Do not mention that you are an AI unless the user asks.
7. Do not say you are a Telegram bot.
8. Be polite, helpful and natural.
9. Do not repeat the user's message unnecessarily.
"""

    # Create input for OpenAI
    input_messages = []

    for message in conversation_history[chat_id]:
        input_messages.append({
            "role": message["role"],
            "content": message["content"]
        })

    # Call OpenAI Responses API
    response = ai.responses.create(
        model="gpt-5.6-luna",
        instructions=instructions,
        input=input_messages,
        max_output_tokens=500
    )

    # Get generated text
    reply = response.output_text.strip()

    # Save AI response to memory
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
# INCOMING TELEGRAM MESSAGES
# ============================================================

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

    if not incoming_message:
        return

    print("\n" + "=" * 60)
    print("NEW MESSAGE")
    print("=" * 60)

    print(f"User: {sender.first_name}")
    print(f"Message: {incoming_message}")

    try:

        # Generate AI reply
        reply = await asyncio.to_thread(
            generate_reply,
            event.chat_id,
            incoming_message
        )

        print(f"AI Reply: {reply}")

        # Send reply
        await event.reply(reply)

        print("Reply sent successfully.")

    except Exception as error:

        print("ERROR:", error)

        # Optional fallback reply
        try:
            await event.reply(
                "Sorry, I couldn't generate a reply right now."
            )
        except Exception:
            pass

    print("=" * 60)


# ============================================================
# MAIN FUNCTION
# ============================================================

async def main():

    print("=" * 60)
    print("AI TELEGRAM AUTO-REPLY")
    print("=" * 60)

    print("Connecting to Telegram...")

    await client.start()

    # Get logged-in account
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

    # Keep program running
    await client.run_until_disconnected()


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nBot stopped.")
