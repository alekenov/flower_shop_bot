import requests
import psycopg2
from psycopg2.extras import DictCursor
import json

def delete_webhook():
    # Получаем токен бота из базы данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT credential_value FROM credentials WHERE service_name = 'telegram' AND credential_key = 'bot_token'")
    bot_token = cur.fetchone()['credential_value']
    
    # URL для удаления webhook
    url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
    
    try:
        # Делаем запрос к API
        response = requests.get(url)
        data = response.json()
        
        print("\nРезультат удаления webhook:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Ошибка при удалении webhook: {str(e)}")

if __name__ == '__main__':
    delete_webhook()
