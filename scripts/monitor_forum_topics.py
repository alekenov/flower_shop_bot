import asyncio
from telegram import Bot
import psycopg2
from psycopg2.extras import DictCursor
import json
import requests

def get_topics():
    # Получаем токен бота из базы данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT credential_value FROM credentials WHERE service_name = 'telegram' AND credential_key = 'bot_token'")
    bot_token = cur.fetchone()['credential_value']
    
    # ID группы "Цветы"
    chat_id = -1001375195020
    
    # URL для получения обновлений
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        # Получаем последние обновления
        response = requests.get(url, params={'limit': 100})  # увеличиваем лимит для получения большего количества сообщений
        data = response.json()
        
        if data.get('ok'):
            # Множество для хранения уникальных тем
            topics = set()
            
            print("\nНайденные темы:")
            for update in data['result']:
                message = update.get('message', {})
                
                # Проверяем наличие ID темы
                thread_id = message.get('message_thread_id')
                if thread_id:
                    # Если есть информация о создании темы
                    topic_info = message.get('forum_topic_created')
                    if topic_info:
                        topic_name = topic_info.get('name', 'Без названия')
                        topics.add(f"ID: {thread_id}, Название: {topic_name} (новая тема)")
                    else:
                        topics.add(f"ID: {thread_id}")
            
            # Выводим уникальные темы
            if topics:
                for topic in sorted(topics):
                    print(topic)
            else:
                print("Темы не найдены в последних обновлениях")
                
            print("\nПолное содержимое ответа API:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"Ошибка API: {data.get('description')}")
            
    except Exception as e:
        print(f"Ошибка при получении тем: {str(e)}")

if __name__ == '__main__':
    get_topics()
