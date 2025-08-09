import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import logging
import urllib.parse

# ===== CONFIG =====
BOT_TOKEN = "8222388134:AAFc5tmFHPaNFY1EBCFm0Y2xUqwG0BcYPbQ"
CSE_ID = "441401868adeb4250"

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== FUNCTION TO GET CSE JSON RESULTS =====
def cse_search(query: str):
    encoded_q = urllib.parse.quote(query)
    # This is CSE's hidden JSON endpoint
    url = f"https://cse.google.com/cse/element/v1?rsz=filtered_cse&num=5&hl=en&cx={CSE_ID}&q={encoded_q}&safe=off&cse_tok=&exp=csqr,cc&callback=google.search.cse.api2611"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        return []

    # The response is JSONP, so we strip the callback wrapper
    raw = r.text
    try:
        json_str = raw[raw.index("{") : raw.rindex("}") + 1]
        data = requests.utils.json.loads(json_str)
    except Exception as e:
        logger.error(f"Failed to parse CSE JSON: {e}")
        return []

    if "results" not in data:
        return []

    results = []
    for item in data["results"]:
        title = item.get("title", "")
        link = item.get("url", "")
        snippet = item.get("content", "").replace("<b>", "").replace("</b>", "")
        results.append((title, link, snippet))

    return results

# ===== COMMAND HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send /search <query> to search Google via CSE.")

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <query>")
        return

    query = " ".join(context.args)
    results = cse_search(query)

    if not results:
        await update.message.reply_text("No results found.")
        return

    msg = f"🔍 Results for: {query}\n\n"
    for i, (title, link, snippet) in enumerate(results, start=1):
        msg += f"{i}. <b>{title}</b>\n{snippet}\n{link}\n\n"

    await update.message.reply_html(msg)

# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_cmd))
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()