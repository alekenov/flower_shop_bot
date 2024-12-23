import requests
import psycopg2
from psycopg2.extras import DictCursor
import json

def get_topic_messages():
    # Получаем токен бота из базы данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT credential_value FROM credentials WHERE service_name = 'telegram' AND credential_key = 'bot_token'")
    bot_token = cur.fetchone()['credential_value']
    
    # ID группы "Цветы" и ID темы
    chat_id = -1001375195020
    message_thread_id = 85593
    
    # URL для получения сообщений
    url = f"https://api.telegram.org/bot{bot_token}/getMessages"
    
    try:
        # Делаем запрос к API
        params = {
            'chat_id': chat_id,
            'message_thread_id': message_thread_id,
            'limit': 10  # получаем последние 10 сообщений
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        print("\nСообщения из темы:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Ошибка при получении сообщений: {str(e)}")

if __name__ == '__main__':
    get_topic_messages()
