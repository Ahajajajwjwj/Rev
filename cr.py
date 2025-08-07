import logging
import os
import json
import asyncio
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters
)

# ========= CONFIGURATION =========

BOT_TOKEN = "8182613736:AAESfxF6WK8srcgCYEKkJtFii4BXsD6WLXk"
STORE_CHANNEL_ID = -1002893816996
DATA_FILE = "file_data.json"

# ========= LOGGING =========

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========= FILE DB HANDLING =========

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

def save_file_data(file_id, msg_id):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    data[file_id] = msg_id
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_file_msg_id(file_id):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data.get(file_id)

# ========= HANDLERS =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to File Store Bot!\n\n"
        "📤 Send any file (APK, PDF, Photo, etc.)\n"
        "🧾 You'll get a file code.\n"
        "📥 Send that code anytime to get the file back."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Check supported file types
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

    # Simulate uploading animation by editing a progress message
    progress_message = await message.reply_text("⏳ Uploading... [░░░░░░░░░░] 0%")
    total_steps = 10
    for i in range(1, total_steps + 1):
        percentage = i * 10
        progress_bar = "█" * i + "░" * (total_steps - i)
        try:
            await progress_message.edit_text(f"⏳ Uploading... [{progress_bar}] {percentage}%")
        except Exception as e:
            logger.warning(f"Failed to update progress message: {e}")
        await asyncio.sleep(0.3)  # Slight delay to simulate progress

    try:
        # Forward to storage channel
        forwarded = await message.forward(chat_id=STORE_CHANNEL_ID)
        file_id = str(forwarded.message_id)
        save_file_data(file_id, forwarded.message_id)

        await progress_message.edit_text(
            f"✅ File Saved!\n🧾 Your file code:\n\n`{file_id}`\n\n"
            "📥 Send this code to retrieve the file.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        await progress_message.edit_text("⚠️ Failed to save file.")

async def retrieve_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()

    if not code.isdigit():
        await update.message.reply_text("❌ Invalid code. Send only the numeric file code.")
        return

    msg_id = get_file_msg_id(code)
    if not msg_id:
        await update.message.reply_text("❌ File not found.")
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

# ========= RUN BOT WITH INFINITE LOOP =========

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.VOICE, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, retrieve_file))

    print("✅ Bot is running...")
    app.run_polling()

def main():
    while True:
        try:
            run_bot()
        except Exception as e:
            logger.error(f"Bot crashed with error: {e}")
            print("🔄 Restarting bot in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
