import requests
import os
import httpx
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Получаем токен из переменной окружения
TOKEN = os.getenv("BOT")
NGROK_URL = "https://80c7-89-236-247-151.ngrok-free.app"  # Ваш ngrok URL
print("TOKEN:", TOKEN)
webhook_url = f"{NGROK_URL}/webhook/"
url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
response = httpx.post(url, json={"url": webhook_url})
# Отладочные сообщения
print("Статус код:", response.status_code)
print("Ответ сервера:", response.json())
print(response.text)
print(webhook_url) # Шу узгаруччанни кийматини .env файлига WEBHOOK_URL кийматига курсатиш керак
