import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = "https://dkohweivbdwweyvyvcbc.supabase.co/functions/v1/telegram-bot"

def set_webhook():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    data = {
        "url": WEBHOOK_URL,
        "allowed_updates": ["message", "callback_query"]
    }
    response = requests.post(url, json=data)
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    set_webhook()
