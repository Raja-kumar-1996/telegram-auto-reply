import os
import asyncio
from datetime import datetime

from dotenv import load_dotenv

from telethon import TelegramClient, events, Button
from telethon.tl.functions.account import GetAuthorizationsRequest

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.units import mm
from xml.sax.saxutils import escape


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_OWNER_ID = 8420696977

AUTO_REPLY = (
    "Hello! 👋\n"
    "I received your message.\n"
    "We will get back to you soon."
)

BOT_SESSION = "telegram_auto_reply"
USER_SESSION = "telegram_history"

COMMANDS = {
    "/start",
    "/panel",
    "/history",
    "/devices",
    "/grant",
    "/revoke",
}


# ============================================================
# VALIDATE CONFIGURATION
# ============================================================

if not API_ID:
    raise ValueError("API_ID is missing from .env")

if not API_HASH:
    raise ValueError("API_HASH is missing from .env")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing from .env")

try:
    API_ID = int(API_ID)
except ValueError:
    raise ValueError("API_ID must be a number")


# ============================================================
# TELEGRAM CLIENTS
# ============================================================

bot_client = TelegramClient(
    BOT_SESSION,
    API_ID,
    API_HASH
)

user_client = TelegramClient(
    USER_SESSION,
    API_ID,
    API_HASH
)


# ============================================================
# AUTHORIZED USERS
# ============================================================

authorized_users = {
    BOT_OWNER_ID
}


# ============================================================
# DUPLICATE MESSAGE PROTECTION
# ============================================================

processed_messages = set()

user_me_id = None


# ============================================================
# PDF DIRECTORY
# ============================================================

PDF_DIRECTORY = "history_pdfs"

os.makedirs(
    PDF_DIRECTORY,
    exist_ok=True
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def is_owner(user_id):
    return user_id == BOT_OWNER_ID


def is_authorized(user_id):
    return user_id in authorized_users


def get_sender_name(sender):

    if not sender:
        return "Unknown"

    first_name = sender.first_name or ""
    last_name = sender.last_name or ""

    name = f"{first_name} {last_name}".strip()

    return name or "Unknown"


def get_username(sender):

    if not sender:
        return "None"

    if sender.username:
        return f"@{sender.username}"

    return "None"


async def send_long_message(
    event,
    text,
    limit=4000
):

    if len(text) <= limit:

        await event.respond(text)

        return

    chunks = []

    while text:

        if len(text) <= limit:

            chunks.append(text)

            break

        split_at = text.rfind(
            "\n",
            0,
            limit
        )

        if split_at <= 0:
            split_at = limit

        chunks.append(
            text[:split_at]
        )

        text = text[
            split_at:
        ].lstrip("\n")

    for chunk in chunks:

        await event.respond(
            chunk
        )


async def notify_owner(
    sender,
    message
):

    name = get_sender_name(sender)
    username = get_username(sender)
    user_id = sender.id

    notification = (
        "📩 NEW PRIVATE MESSAGE\n\n"
        f"Name     : {name}\n"
        f"Username : {username}\n"
        f"User ID  : {user_id}\n"
        f"Message  : {message}"
    )

    try:

        await bot_client.send_message(
            BOT_OWNER_ID,
            notification
        )

    except Exception as exc:

        print()
        print("OWNER NOTIFICATION FAILED")
        print(
            f"Exception: "
            f"{type(exc).__name__}: {exc}"
        )
        print()


# ============================================================
# PROGRESS ANIMATION
# ============================================================

async def progress_animation(
    message,
    stop_event
):

    frames = [
        "⏳ Preparing history",
        "🔎 Fetching messages",
        "📊 Processing history",
        "📄 Creating PDF",
        "📤 Preparing download"
    ]

    index = 0

    while not stop_event.is_set():

        try:

            await message.edit(
                frames[index % len(frames)]
                + "."
            )

        except Exception:
            pass

        index += 1

        try:

            await asyncio.wait_for(
                stop_event.wait(),
                timeout=0.8
            )

        except asyncio.TimeoutError:

            continue


# ============================================================
# CREATE PDF
# ============================================================

def create_history_pdf(
    user_id,
    name,
    username,
    messages
):

    safe_username = (
        username
        .replace("@", "")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"telegram_history_"
        f"{user_id}_"
        f"{timestamp}.pdf"
    )

    filepath = os.path.join(
        PDF_DIRECTORY,
        filename
    )

    document = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "HistoryTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "HistoryHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=8,
        spaceAfter=6,
    )

    message_style = ParagraphStyle(
        "HistoryMessage",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=4,
    )

    small_style = ParagraphStyle(
        "HistorySmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    story = []

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "📜 TELEGRAM MESSAGE HISTORY",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Generated by Telegram Automation Bot",
            small_style
        )
    )

    story.append(
        Spacer(
            1,
            8
        )
    )

    # --------------------------------------------------------
    # USER INFORMATION
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "👤 USER INFORMATION",
            heading_style
        )
    )

    user_data = [
        ["User ID", str(user_id)],
        ["Name", escape(name)],
        ["Username", escape(username)],
        [
            "Total Messages",
            str(len(messages))
        ],
        [
            "Generated",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ],
    ]

    user_table = Table(
        user_data,
        colWidths=[
            45 * mm,
            125 * mm
        ]
    )

    user_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.lightgrey
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    "Helvetica"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
            ]
        )
    )

    story.append(
        user_table
    )

    story.append(
        Spacer(
            1,
            12
        )
    )

    # --------------------------------------------------------
    # MESSAGE HISTORY
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "💬 MESSAGE HISTORY",
            heading_style
        )
    )

    if not messages:

        story.append(
            Paragraph(
                "No accessible text messages were found.",
                message_style
            )
        )

    else:

        for number, msg in enumerate(
            messages,
            start=1
        ):

            msg_date = msg.date

            if msg_date:

                try:

                    date_text = msg_date.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                except Exception:

                    date_text = str(msg_date)

            else:

                date_text = "Unknown"

            sender_id = (
                msg.sender_id
                if msg.sender_id
                else "Unknown"
            )

            text = (
                msg.message
                if msg.message
                else "[Media / Non-text message]"
            )

            text = escape(
                str(text)
            )

            text = text.replace(
                "\n",
                "<br/>"
            )

            header = (
                f"<b>Message #{number}</b> "
                f"| {date_text} "
                f"| Sender ID: {sender_id}"
            )

            story.append(
                Paragraph(
                    header,
                    message_style
                )
            )

            story.append(
                Paragraph(
                    text,
                    message_style
                )
            )

            story.append(
                Spacer(
                    1,
                    5
                )
            )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    story.append(
        Spacer(
            1,
            12
        )
    )

    story.append(
        Paragraph(
            "End of Telegram history.",
            small_style
        )
    )

    document.build(
        story
    )

    return filepath


# ============================================================
# FEATURE 1
# PRIVATE MESSAGE READER
# FEATURE 2
# AUTO REPLY
# FEATURE 3
# OWNER NOTIFICATION
# ============================================================

@bot_client.on(
    events.NewMessage(
        incoming=True
    )
)
async def private_message_handler(
    event
):

    if not event.is_private:
        return

    message_key = (
        event.chat_id,
        event.id
    )

    if message_key in processed_messages:
        return

    processed_messages.add(
        message_key
    )

    sender = await event.get_sender()

    if not sender:
        return

    user_id = sender.id

    name = get_sender_name(
        sender
    )

    username = get_username(
        sender
    )

    message = event.raw_text

    date_time = event.date

    print()
    print("=" * 60)
    print("PRIVATE MESSAGE RECEIVED")
    print("=" * 60)
    print(
        f"User ID  : {user_id}"
    )
    print(
        f"Name     : {name}"
    )
    print(
        f"Username : {username}"
    )
    print(
        f"Message  : {message}"
    )
    print(
        f"Date/Time: {date_time}"
    )
    print("=" * 60)
    print()

    await notify_owner(
        sender,
        message
    )

    command = (
        message.strip()
        .split()[0]
        .lower()
        if message.strip()
        else ""
    )

    if command in COMMANDS:
        return

    try:

        await event.respond(
            AUTO_REPLY
        )

        print(
            "AUTO-REPLY SENT"
        )
        print()

    except Exception as exc:

        print()
        print(
            "AUTO-REPLY FAILED"
        )
        print(
            f"Exception: "
            f"{type(exc).__name__}: {exc}"
        )
        print()


# ============================================================
# /start
# ============================================================

@bot_client.on(
    events.NewMessage(
        pattern=r"^/start(?:\s+.*)?$"
    )
)
async def start_command(event):

    if not event.is_private:
        return

    await event.respond(
        "👋 Welcome!\n\n"
        "Your message has been received."
    )


# ============================================================
# /panel
# ============================================================

@bot_client.on(
    events.NewMessage(
        pattern=r"^/panel(?:\s+.*)?$"
    )
)
async def panel_command(event):

    if not event.is_private:
        return

    sender = await event.get_sender()

    if not sender or not is_owner(
        sender.id
    ):

        await event.respond(
            "❌ Owner only."
        )

        return

    await event.respond(
        "⚙️ ADMIN PANEL",
        buttons=[
            [
                Button.inline(
                    "👥 Authorized Users",
                    b"authorized_users"
                )
            ],
            [
                Button.inline(
                    "➕ Grant Access",
                    b"grant_help"
                ),
                Button.inline(
                    "🔴 Revoke Access",
                    b"revoke_help"
                )
            ],
            [
                Button.inline(
                    "📱 Active Devices",
                    b"active_devices"
                )
            ]
        ]
    )


# ============================================================
# /grant USER_ID
# ============================================================

@bot_client.on(
    events.NewMessage(
        pattern=r"^/grant(?:\s+(\d+))?$"
    )
)
async def grant_command(event):

    if not event.is_private:
        return

    sender = await event.get_sender()

    if not sender or not is_owner(
        sender.id
    ):

        await event.respond(
            "❌ Owner only."
        )

        return

    user_id_text = (
        event.pattern_match.group(1)
    )

    if not user_id_text:

        await event.respond(
            "Usage:\n"
            "/grant USER_ID"
        )

        return

    user_id = int(
        user_id_text
    )

    if user_id == BOT_OWNER_ID:

        await event.respond(
            "ℹ️ The owner is always authorized."
        )

        return

    authorized_users.add(
        user_id
    )

    await event.respond(
        "✅ ACCESS GRANTED\n\n"
        f"User ID: {user_id}"
    )


# ============================================================
# /revoke USER_ID
# ============================================================

@bot_client.on(
    events.NewMessage(
        pattern=r"^/revoke(?:\s+(\d+))?$"
    )
)
async def revoke_command(event):

    if not event.is_private:
        return

    sender = await event.get_sender()

    if not sender or not is_owner(
        sender.id
    ):

        await event.respond(
            "❌ Owner only."
        )

        return

    user_id_text = (
        event.pattern_match.group(1)
    )

    if not user_id_text:

        await event.respond(
            "Usage:\n"
            "/revoke USER_ID"
        )

        return

    user_id = int(
        user_id_text
    )

    if user_id == BOT_OWNER_ID:

        await event.respond(
            "❌ The owner cannot be revoked."
        )

        return

    if user_id not in authorized_users:

        await event.respond(
            f"ℹ️ User {user_id} "
            "is not currently authorized."
        )

        return

    await event.respond(
        "⚠️ REVOKE ACCESS\n\n"
        f"User ID: {user_id}",
        buttons=[
            [
                Button.inline(
                    "✅ Confirm Revoke",
                    f"confirm_revoke:{user_id}".encode()
                ),
                Button.inline(
                    "❌ Cancel",
                    b"cancel_revoke"
                )
            ]
        ]
    )


# ============================================================
# /devices
# ============================================================

@bot_client.on(
    events.NewMessage(
        pattern=r"^/devices$"
    )
)
async def devices_command(event):

    if not event.is_private:
        return

    sender = await event.get_sender()

    if not sender or not is_owner(
        sender.id
    ):

        await event.respond(
            "❌ Owner only."
        )

        return

    await show_devices(
        event
    )


async def show_devices(event):

    try:

        authorizations = await user_client(
            GetAuthorizationsRequest()
        )

    except Exception as exc:

        await event.respond(
            "❌ Could not retrieve "
            "Telegram sessions.\n\n"
            f"Error: {type(exc).__name__}: {exc}"
        )

        return

    sessions = (
        authorizations.authorizations
    )

    output = []

    output.append(
        "📱 ACTIVE TELEGRAM SESSIONS"
    )

    output.append(
        "=" * 50
    )

    output.append(
        f"Total sessions: {len(sessions)}"
    )

    output.append("")

    for number, session in enumerate(
        sessions,
        start=1
    ):

        current = (
            "CURRENT"
            if session.current
            else "OTHER"
        )

        output.append(
            f"SESSION #{number}"
        )

        output.append(
            f"Status         : {current}"
        )

        output.append(
            f"Device Model   : "
            f"{session.device_model or 'Unknown'}"
        )

        output.append(
            f"Platform       : "
            f"{session.platform or 'Unknown'}"
        )

        output.append(
            f"App Version    : "
            f"{session.app_version or 'Unknown'}"
        )

        output.append(
            f"System Version : "
            f"{session.system_version or 'Unknown'}"
        )

        output.append(
            f"IP Address     : "
            f"{session.ip or 'Unknown'}"
        )

        output.append(
            f"Country        : "
            f"{session.country or 'Unknown'}"
        )

        output.append(
            f"Last Active    : "
            f"{session.date_active}"
        )

        output.append("")

    await send_long_message(
        event,
        "\n".join(output)
    )


# ============================================================
# /history USER_ID
# PDF VERSION
# ============================================================

@bot_client.on(
    events.NewMessage(
        pattern=r"^/history\s+(\d+)$"
    )
)
async def history_command(event):

    if not event.is_private:
        return

    sender = await event.get_sender()

    if not sender or not is_owner(
        sender.id
    ):

        await event.respond(
            "❌ Owner only."
        )

        return

    user_id = int(
        event.pattern_match.group(1)
    )

    # --------------------------------------------------------
    # PROGRESS MESSAGE
    # --------------------------------------------------------

    progress_message = await event.respond(
        "⏳ Preparing history..."
    )

    stop_animation = asyncio.Event()

    animation_task = asyncio.create_task(
        progress_animation(
            progress_message,
            stop_animation
        )
    )

    filepath = None

    try:

        # ----------------------------------------------------
        # GET USER
        # ----------------------------------------------------

        try:

            entity = await user_client.get_entity(
                user_id
            )

        except Exception as exc:

            await progress_message.edit(
                "❌ Could not access this Telegram user.\n\n"
                f"Error: {type(exc).__name__}: {exc}"
            )

            return

        name = get_sender_name(
            entity
        )

        username = get_username(
            entity
        )

        # ----------------------------------------------------
        # FETCH HISTORY
        # ----------------------------------------------------

        messages = []

        async for msg in user_client.iter_messages(
            entity,
            limit=100
        ):

            # Keep messages with text.
            # Media-only messages are also kept
            # so the PDF can report them.
            if msg.message:

                messages.append(
                    msg
                )

            elif msg.media:

                messages.append(
                    msg
                )

        # ----------------------------------------------------
        # CREATE PDF
        # ----------------------------------------------------

        filepath = await asyncio.to_thread(
            create_history_pdf,
            user_id,
            name,
            username,
            messages
        )

        # ----------------------------------------------------
        # STOP ANIMATION
        # ----------------------------------------------------

        stop_animation.set()

        await animation_task

        # ----------------------------------------------------
        # SEND PDF
        # ----------------------------------------------------

        await progress_message.edit(
            "📤 Uploading PDF..."
        )

        caption = (
            "📜 TELEGRAM HISTORY\n\n"
            f"👤 Name: {name}\n"
            f"🔹 Username: {username}\n"
            f"🆔 User ID: {user_id}\n"
            f"💬 Messages: {len(messages)}\n\n"
            "📄 PDF generated successfully."
        )

        await bot_client.send_file(
            event.chat_id,
            filepath,
            caption=caption
        )

        await progress_message.delete()

        print()
        print(
            "=" * 60
        )
        print(
            "HISTORY PDF CREATED"
        )
        print(
            "=" * 60
        )
        print(
            f"User ID : {user_id}"
        )
        print(
            f"Name    : {name}"
        )
        print(
            f"Messages: {len(messages)}"
        )
        print(
            f"PDF     : {filepath}"
        )
        print(
            "=" * 60
        )
        print()

    except Exception as exc:

        stop_animation.set()

        try:
            await animation_task
        except Exception:
            pass

        try:

            await progress_message.edit(
                "❌ HISTORY PDF FAILED\n\n"
                f"Error: {type(exc).__name__}: {exc}"
            )

        except Exception:
            pass

        print()
        print(
            "HISTORY PDF FAILED"
        )
        print(
            f"Exception: "
            f"{type(exc).__name__}: {exc}"
        )
        print()

    finally:

        # ----------------------------------------------------
        # DELETE LOCAL PDF AFTER UPLOAD
        # ----------------------------------------------------

        if filepath and os.path.exists(
            filepath
        ):

            try:

                os.remove(
                    filepath
                )

            except Exception:
                pass


# ============================================================
# /history USER_ID_1 USER_ID_2
# ============================================================



# ============================================================
# PAIR HISTORY PDF
# ============================================================

def create_pair_history_pdf(
    user_id_1,
    name_1,
    username_1,
    user_id_2,
    name_2,
    username_2,
    messages
):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"telegram_conversation_"
        f"{user_id_1}_{user_id_2}_"
        f"{timestamp}.pdf"
    )

    filepath = os.path.join(
        PDF_DIRECTORY,
        filename
    )

    document = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PairTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "PairHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=8,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "PairBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=4,
    )

    small_style = ParagraphStyle(
        "PairSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
    )

    story = []

    story.append(
        Paragraph(
            "📜 TELEGRAM CONVERSATION HISTORY",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Generated by Telegram Automation Bot",
            small_style
        )
    )

    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "👥 PARTICIPANTS",
            heading_style
        )
    )

    participants = [
        ["User", "Name", "Username", "User ID"],
        [
            "A",
            escape(name_1),
            escape(username_1),
            str(user_id_1)
        ],
        [
            "B",
            escape(name_2),
            escape(username_2),
            str(user_id_2)
        ],
    ]

    table = Table(
        participants,
        colWidths=[
            15 * mm,
            55 * mm,
            45 * mm,
            45 * mm
        ]
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
            ]
        )
    )

    story.append(table)

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            f"💬 MESSAGE HISTORY — {len(messages)} messages",
            heading_style
        )
    )

    if not messages:

        story.append(
            Paragraph(
                "No accessible messages were found.",
                body_style
            )
        )

    else:

        for number, msg in enumerate(
            messages,
            start=1
        ):

            date_text = (
                msg.date.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if msg.date
                else "Unknown"
            )

            sender_id = (
                msg.sender_id
                if msg.sender_id
                else "Unknown"
            )

            message_text = (
                msg.message
                if msg.message
                else "[Media / Non-text message]"
            )

            message_text = escape(
                str(message_text)
            ).replace(
                "\n",
                "<br/>"
            )

            story.append(
                Paragraph(
                    f"<b>Message #{number}</b> | "
                    f"{date_text} | "
                    f"Sender ID: {sender_id}",
                    body_style
                )
            )

            story.append(
                Paragraph(
                    message_text,
                    body_style
                )
            )

            story.append(
                Spacer(1, 5)
            )

    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            "End of accessible Telegram conversation history.",
            small_style
        )
    )

    document.build(story)

    return filepath

@bot_client.on(
    events.NewMessage(
        pattern=r"^/history\s+(\d+)\s+(\d+)$"
    )
)
async def pair_history_command(event):

    if not event.is_private:
        return

    sender = await event.get_sender()

    if not sender or not is_owner(sender.id):
        await event.respond("❌ Owner only.")
        return

    user_id_1 = int(event.pattern_match.group(1))
    user_id_2 = int(event.pattern_match.group(2))

    # --------------------------------------------------------
    # PROGRESS MESSAGE
    # --------------------------------------------------------

    progress_message = await event.respond(
        "⏳ Preparing conversation history..."
    )

    stop_animation = asyncio.Event()

    animation_task = asyncio.create_task(
        progress_animation(
            progress_message,
            stop_animation
        )
    )

    filepath = None

    try:

        # ----------------------------------------------------
        # GET BOTH USERS
        # ----------------------------------------------------

        try:
            entity_1 = await user_client.get_entity(
                user_id_1
            )

            entity_2 = await user_client.get_entity(
                user_id_2
            )

        except Exception as exc:

            await progress_message.edit(
                "❌ One or both users are not accessible "
                "to the normal Telegram account.\n\n"
                f"Error: {type(exc).__name__}: {exc}"
            )

            return

        name_1 = get_sender_name(entity_1)
        username_1 = get_username(entity_1)

        name_2 = get_sender_name(entity_2)
        username_2 = get_username(entity_2)

        # ----------------------------------------------------
        # FIND ACCESSIBLE PRIVATE CHAT
        # ----------------------------------------------------

        chat_entity = None

        try:

            dialogs = user_client.iter_dialogs()

            async for dialog in dialogs:

                if not dialog.is_user:
                    continue

                dialog_user = dialog.entity

                if not dialog_user:
                    continue

                dialog_id = dialog_user.id

                if (
                    dialog_id == user_id_1
                    and user_id_2 == user_me_id
                ):
                    chat_entity = dialog.entity
                    break

                if (
                    dialog_id == user_id_2
                    and user_id_1 == user_me_id
                ):
                    chat_entity = dialog.entity
                    break

                # If both IDs are users other than the
                # logged-in account, Telegram may expose
                # a mutual/group chat instead. We do not
                # guess or bypass privacy.
                if dialog_id in (
                    user_id_1,
                    user_id_2
                ):
                    if dialog.is_user:
                        chat_entity = dialog.entity

            if chat_entity is None:

                await progress_message.edit(
                    "❌ No accessible private conversation "
                    "was found for these users.\n\n"
                    "The normal Telegram account must "
                    "legitimately have access to the chat."
                )

                return

        except Exception as exc:

            await progress_message.edit(
                "❌ Could not inspect Telegram dialogs.\n\n"
                f"Error: {type(exc).__name__}: {exc}"
            )

            return

        # ----------------------------------------------------
        # FETCH MESSAGES
        # ----------------------------------------------------

        messages = []

        async for msg in user_client.iter_messages(
            chat_entity,
            limit=100
        ):

            if msg.message or msg.media:
                messages.append(msg)

        # ----------------------------------------------------
        # CREATE PDF
        # ----------------------------------------------------

        await progress_message.edit(
            "📄 Creating conversation PDF..."
        )

        filepath = await asyncio.to_thread(
            create_pair_history_pdf,
            user_id_1,
            name_1,
            username_1,
            user_id_2,
            name_2,
            username_2,
            messages
        )

        # ----------------------------------------------------
        # STOP ANIMATION
        # ----------------------------------------------------

        stop_animation.set()

        try:
            await animation_task
        except Exception:
            pass

        # ----------------------------------------------------
        # UPLOAD PDF
        # ----------------------------------------------------

        await progress_message.edit(
            "📤 Uploading PDF..."
        )

        caption = (
            "📜 TELEGRAM CONVERSATION HISTORY\n\n"
            f"👤 User A: {name_1}\n"
            f"🔹 {username_1}\n"
            f"🆔 {user_id_1}\n\n"
            f"👤 User B: {name_2}\n"
            f"🔹 {username_2}\n"
            f"🆔 {user_id_2}\n\n"
            f"💬 Messages: {len(messages)}\n\n"
            "📄 PDF generated successfully."
        )

        await bot_client.send_file(
            event.chat_id,
            filepath,
            caption=caption
        )

        await progress_message.delete()

        print()
        print("=" * 60)
        print("PAIR HISTORY PDF CREATED")
        print("=" * 60)
        print(f"User A  : {user_id_1}")
        print(f"User B  : {user_id_2}")
        print(f"Messages: {len(messages)}")
        print(f"PDF     : {filepath}")
        print("=" * 60)
        print()

    except Exception as exc:

        stop_animation.set()

        try:
            await animation_task
        except Exception:
            pass

        try:
            await progress_message.edit(
                "❌ PAIR HISTORY PDF FAILED\n\n"
                f"Error: {type(exc).__name__}: {exc}"
            )
        except Exception:
            pass

        print()
        print("PAIR HISTORY PDF FAILED")
        print(
            f"Exception: "
            f"{type(exc).__name__}: {exc}"
        )
        print()

    finally:

        if filepath and os.path.exists(filepath):

            try:
                os.remove(filepath)
            except Exception:
                pass


# ============================================================
# CALLBACK HANDLER
# ============================================================

@bot_client.on(
    events.CallbackQuery
)
async def callback_handler(event):

    sender = await event.get_sender()

    if not sender or not is_owner(
        sender.id
    ):

        await event.answer(
            "Owner only.",
            alert=True
        )

        return

    data = event.data.decode(
        "utf-8"
    )

    # --------------------------------------------------------
    # AUTHORIZED USERS
    # --------------------------------------------------------

    if data == "authorized_users":

        users = sorted(
            authorized_users
        )

        text = (
            "👥 AUTHORIZED USERS\n\n"
            f"Total: {len(users)}\n\n"
        )

        for user_id in users:

            if user_id == BOT_OWNER_ID:

                text += (
                    f"👑 {user_id} — OWNER\n"
                )

            else:

                text += (
                    f"✅ {user_id}\n"
                )

        await event.edit(
            text,
            buttons=[
                [
                    Button.inline(
                        "⬅️ Back",
                        b"panel_back"
                    )
                ]
            ]
        )

        return

    # --------------------------------------------------------
    # GRANT HELP
    # --------------------------------------------------------

    if data == "grant_help":

        await event.edit(
            "➕ GRANT ACCESS\n\n"
            "Use:\n"
            "/grant USER_ID",
            buttons=[
                [
                    Button.inline(
                        "⬅️ Back",
                        b"panel_back"
                    )
                ]
            ]
        )

        return

    # --------------------------------------------------------
    # REVOKE HELP
    # --------------------------------------------------------

    if data == "revoke_help":

        await event.edit(
            "🔴 REVOKE ACCESS\n\n"
            "Use:\n"
            "/revoke USER_ID\n\n"
            "You will receive a confirmation "
            "before access is removed.",
            buttons=[
                [
                    Button.inline(
                        "⬅️ Back",
                        b"panel_back"
                    )
                ]
            ]
        )

        return

    # --------------------------------------------------------
    # ACTIVE DEVICES
    # --------------------------------------------------------

    if data == "active_devices":

        try:

            authorizations = await user_client(
                GetAuthorizationsRequest()
            )

            sessions = (
                authorizations.authorizations
            )

            text = (
                "📱 ACTIVE DEVICES\n\n"
                f"Total sessions: "
                f"{len(sessions)}\n\n"
            )

            for number, session in enumerate(
                sessions,
                start=1
            ):

                current = (
                    "CURRENT"
                    if session.current
                    else "OTHER"
                )

                text += (
                    f"SESSION #{number}\n"
                    f"Status: {current}\n"
                    f"Device: "
                    f"{session.device_model or 'Unknown'}\n"
                    f"Platform: "
                    f"{session.platform or 'Unknown'}\n"
                    f"App: "
                    f"{session.app_version or 'Unknown'}\n"
                    f"System: "
                    f"{session.system_version or 'Unknown'}\n"
                    f"IP: "
                    f"{session.ip or 'Unknown'}\n"
                    f"Country: "
                    f"{session.country or 'Unknown'}\n"
                    f"Last active: "
                    f"{session.date_active}\n\n"
                )

            await send_callback_text(
                event,
                text
            )

        except Exception as exc:

            await send_callback_text(
                event,
                "❌ DEVICE REQUEST FAILED\n\n"
                f"{type(exc).__name__}: {exc}"
            )

        return

    # --------------------------------------------------------
    # CONFIRM REVOKE
    # --------------------------------------------------------

    if data.startswith(
        "confirm_revoke:"
    ):

        user_id = int(
            data.split(
                ":",
                1
            )[1]
        )

        if user_id == BOT_OWNER_ID:

            await event.edit(
                "❌ The owner cannot be revoked."
            )

            return

        if user_id in authorized_users:

            authorized_users.remove(
                user_id
            )

            await event.edit(
                "✅ ACCESS REVOKED\n\n"
                f"User ID: {user_id}"
            )

        else:

            await event.edit(
                "ℹ️ That user is not currently authorized."
            )

        return

    # --------------------------------------------------------
    # CANCEL REVOKE
    # --------------------------------------------------------

    if data == "cancel_revoke":

        await event.edit(
            "❌ Revoke cancelled."
        )

        return

    # --------------------------------------------------------
    # BACK TO PANEL
    # --------------------------------------------------------

    if data == "panel_back":

        await event.edit(
            "⚙️ ADMIN PANEL",
            buttons=[
                [
                    Button.inline(
                        "👥 Authorized Users",
                        b"authorized_users"
                    )
                ],
                [
                    Button.inline(
                        "➕ Grant Access",
                        b"grant_help"
                    ),
                    Button.inline(
                        "🔴 Revoke Access",
                        b"revoke_help"
                    )
                ],
                [
                    Button.inline(
                        "📱 Active Devices",
                        b"active_devices"
                    )
                ]
            ]
        )

        return


# ============================================================
# CALLBACK TEXT
# ============================================================

async def send_callback_text(
    event,
    text
):

    if len(text) <= 4000:

        await event.edit(
            text,
            buttons=[
                [
                    Button.inline(
                        "⬅️ Back",
                        b"panel_back"
                    )
                ]
            ]
        )

        return

    await event.edit(
        text[:3900],
        buttons=[
            [
                Button.inline(
                    "⬅️ Back",
                    b"panel_back"
                )
            ]
        ]
    )


# ============================================================
# START BOTH CLIENTS
# ============================================================

async def main():

    global user_me_id

    print()
    print("=" * 60)
    print(
        "STARTING TELEGRAM AUTOMATION"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # BOT CLIENT
    # --------------------------------------------------------

    print()
    print(
        "Starting bot client..."
    )

    await bot_client.start(
        bot_token=BOT_TOKEN
    )

    bot_me = await bot_client.get_me()

    print()
    print(
        "BOT ACCOUNT"
    )

    print(
        f"Name     : "
        f"{get_sender_name(bot_me)}"
    )

    print(
        f"Username : "
        f"{get_username(bot_me)}"
    )

    print(
        f"User ID  : "
        f"{bot_me.id}"
    )

    # --------------------------------------------------------
    # NORMAL USER CLIENT
    # --------------------------------------------------------

    print()
    print(
        "Starting normal Telegram user client..."
    )

    await user_client.start()

    user_me = await user_client.get_me()

    user_me_id = user_me.id

    print()
    print(
        "NORMAL USER ACCOUNT"
    )

    print(
        f"Name     : "
        f"{get_sender_name(user_me)}"
    )

    print(
        f"Username : "
        f"{get_username(user_me)}"
    )

    print(
        f"User ID  : "
        f"{user_me.id}"
    )

    # --------------------------------------------------------
    # SECURITY CHECK
    # --------------------------------------------------------

    if user_me.id == BOT_OWNER_ID:

        print()
        print(
            "Owner account verified."
        )

    else:

        print()
        print(
            "WARNING: Normal Telegram account "
            "ID does not match BOT_OWNER_ID."
        )

        print(
            f"Expected: {BOT_OWNER_ID}"
        )

        print(
            f"Actual  : {user_me.id}"
        )

    # --------------------------------------------------------
    # RUNNING
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "TELEGRAM AUTOMATION IS RUNNING"
    )
    print("=" * 60)

    print()
    print(
        "Bot      : @DGCommunite_bot"
    )

    print(
        "Owner ID : 8420696977"
    )

    print()
    print(
        "Features:"
    )

    print(
        "  ✓ Private message reader"
    )

    print(
        "  ✓ Auto reply"
    )

    print(
        "  ✓ Owner notification"
    )

    print(
        "  ✓ /start"
    )

    print(
        "  ✓ /history"
    )

    print(
        "  ✓ PDF history download"
    )

    print(
        "  ✓ History progress animation"
    )

    print(
        "  ✓ /devices"
    )

    print(
        "  ✓ /panel"
    )

    print(
        "  ✓ /grant"
    )

    print(
        "  ✓ /revoke"
    )

    print()
    print(
        "Waiting for Telegram events..."
    )

    print()

    await asyncio.gather(
        bot_client.run_until_disconnected(),
        user_client.run_until_disconnected()
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "Bot stopped."
        )

    except Exception as exc:

        print()
        print("=" * 60)
        print(
            "PROGRAM FAILED"
        )
        print("=" * 60)
        print(
            f"{type(exc).__name__}: {exc}"
        )
        print("=" * 60)
