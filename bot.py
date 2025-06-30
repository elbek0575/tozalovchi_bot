import threading
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, MessageHandler, filters
from dotenv import load_dotenv
from handlers import delete_if_photo_contains_fake_text, delete_violating_messages

# 📦 .env файлдан токен ва URL ни оламиз
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")

# 🌐 Flask сервер
flask_app = Flask(__name__)
application: Application = ApplicationBuilder().token(TOKEN).build()

# ✅ Хендлерлар
application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, delete_if_photo_contains_fake_text))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), delete_violating_messages))

# 📥 Telegram Webhook POST
@flask_app.route(f"/{TOKEN}", methods=["POST"])
async def webhook_handler():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "OK", 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] {e}", flush=True)
        return "Internal Server Error", 500


# 🔄 Flaskнинг бош саҳифаси
@flask_app.route("/", methods=["GET"])
def index():
    return "Bot is running via webhook", 200

# 🔧 Telegram Webhook'ни ўрнатиш ва PTBни ишга тушириш
async def telegram_part():
    await application.initialize()
    await application.bot.set_webhook(url=f"{APP_URL}/{TOKEN}")
    await application.start()
    print("[BOT STARTED] Webhook server is ready...", flush=True)

# 🧠 Асосий процесс
if __name__ == "__main__":
    threading.Thread(target=lambda: asyncio.run(telegram_part())).start()
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
