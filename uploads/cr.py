import logging
import os
import json
import asyncio
import time
import random
import string
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# ========= CONFIGURATION =========

BOT_TOKEN = "8182613736:AAESfxF6WK8srcgCYEKkJtFii4BXsD6WLXk"
STORE_CHANNEL_ID = -1002893816996
DATA_FILE = "file_data.json"
USER_DATA_FILE = "users.json"
ADMIN_ID = 7251749429  # Your Telegram User ID

# ========= LOGGING =========

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========= INIT FILES =========

# File storing uploaded file data
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

# File storing user IDs
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, "w") as f:
        json.dump([], f)

# ========= HELPERS =========

def generate_file_code(length=20):
    charset = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return ''.join(random.choices(charset, k=length))

def save_file_data(file_code, msg_id):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    data[file_code] = msg_id
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_file_msg_id(file_code):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data.get(file_code)

def add_user(user_id):
    with open(USER_DATA_FILE, "r") as f:
        users = json.load(f)
    if user_id not in users:
        users.append(user_id)
        with open(USER_DATA_FILE, "w") as f:
            json.dump(users, f)

# ========= HANDLERS =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)

    await update.message.reply_text(
        "👋 Welcome to File Store Bot!\n\n"
        "📤 Send any file (APK, PDF, Photo, etc.)\n"
        "🧾 You'll get a secure file code after upload.\n"
        "📥 Send that code anytime to get the file back."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)

    message = update.message
    file_obj = (
        message.document or
        message.video or
        message.audio or
        message.voice or
        (message.photo[-1] if message.photo else None)
    )

    if not file_obj:
        await message.reply_text("❌ Unsupported file type.")
        return

    progress_message = await message.reply_text("⏳ Uploading... [░░░░░░░░░░] 0%")
    total_steps = 10
    for i in range(1, total_steps + 1):
        percentage = i * 10
        progress_bar = "█" * i + "░" * (total_steps - i)
        try:
            await progress_message.edit_text(f"⏳ Uploading... [{progress_bar}] {percentage}%")
        except Exception as e:
            logger.warning(f"Failed to update progress message: {e}")
        await asyncio.sleep(0.3)

    try:
        forwarded = await message.forward(chat_id=STORE_CHANNEL_ID)
        file_code = generate_file_code()
        save_file_data(file_code, forwarded.message_id)

        await progress_message.edit_text(
            f"✅ File Saved!\n\n"
            f"🧾 Your secure file code:\n\n`{file_code}`\n\n"
            "📥 Send this code to retrieve your file.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        await progress_message.edit_text("⚠️ Failed to save file.")

async def retrieve_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)

    code = update.message.text.strip()

    if len(code) < 10:
        await update.message.reply_text("❌ Invalid code. Make sure you pasted the full file code.")
        return

    msg_id = get_file_msg_id(code)
    if not msg_id:
        await update.message.reply_text("❌ File not found. Double-check your code.")
        return

    try:
        await context.bot.copy_message(
            chat_id=update.message.chat_id,
            from_chat_id=STORE_CHANNEL_ID,
            message_id=msg_id
        )
    except Exception as e:
        logger.error(f"Error retrieving file: {e}")
        await update.message.reply_text("⚠️ Failed to retrieve the file.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /broadcast <your message>")
        return

    broadcast_text = " ".join(context.args)
    await update.message.reply_text(f"📢 Broadcasting message...")

    try:
        with open(USER_DATA_FILE, "r") as f:
            users = json.load(f)
    except Exception as e:
        logger.error(f"Failed to read users list: {e}")
        await update.message.reply_text("❌ Failed to load user list.")
        return

    count = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=broadcast_text)
            count += 1
            await asyncio.sleep(0.1)  # Avoid telegram flood
        except Exception as e:
            logger.warning(f"Couldn't send to {user_id}: {e}")

    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

# ========= RUN BOT =========

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))  # Admin broadcast command
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, retrieve_file))

    print("✅ Bot is running...")
    app.run_polling()

def main():
    while True:
        try:
            run_bot()
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            print("🔄 Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
