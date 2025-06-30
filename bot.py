import threading
import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, MessageHandler, filters
from dotenv import load_dotenv
from handlers import delete_if_photo_contains_fake_text, delete_violating_messages
import pytesseract
from PIL import Image

# 📦 .env файлдан токен ва URL ни оламиз
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
APP_URL = os.getenv("APP_URL")

# 🌐 Flask сервер
flask_app = Flask(__name__)
application: Application = ApplicationBuilder().token(TOKEN).build()

# ✅ Хендлерлар
# application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, delete_if_photo_contains_fake_text))
# application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), delete_violating_messages))

# 📥 Telegram Webhook POST
@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook_handler():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)

        # 🛑 Хендлерсиз тўғри ўзи хабар устида ишлаймиз
        if update.message and update.message.photo:
            file = asyncio.run(update.message.photo[-1].get_file())
            file_path = asyncio.run(file.download_to_drive())

            text = pytesseract.image_to_string(Image.open(file_path), lang="rus")
            print(f"[OCR]: {text}")

            if "фальш" in text.lower():
                asyncio.run(update.message.delete())
                print("❌ Хабар ўчирилди (manual logic).")

        return "OK", 200
    except Exception as e:
        print(f"[ERROR] Webhook handler exception: {e}")
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
