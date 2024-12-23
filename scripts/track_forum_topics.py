import asyncio
from telegram import Bot
import psycopg2
from psycopg2.extras import DictCursor
import json
import requests
import time

def create_topics_table(conn):
    """Создаем таблицу для хранения информации о темах"""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS forum_topics (
            thread_id BIGINT PRIMARY KEY,
            chat_id BIGINT,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

def save_topic(conn, chat_id, thread_id, name):
    """Сохраняем информацию о теме в базу данных"""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO forum_topics (thread_id, chat_id, name)
        VALUES (%s, %s, %s)
        ON CONFLICT (thread_id) DO UPDATE 
        SET name = EXCLUDED.name
    """, (thread_id, chat_id, name))
    conn.commit()

def track_topics():
    # Подключаемся к базе данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    
    # Создаем таблицу если её нет
    create_topics_table(conn)
    
    # Получаем токен бота
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT credential_value FROM credentials WHERE service_name = 'telegram' AND credential_key = 'bot_token'")
    bot_token = cur.fetchone()['credential_value']
    
    # URL для получения обновлений
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        # Получаем обновления с большим лимитом
        response = requests.get(url, params={'limit': 100, 'allowed_updates': ['message']})
        data = response.json()
        
        if data.get('ok'):
            updates = data['result']
            print(f"\nПолучено обновлений: {len(updates)}")
            
            for update in updates:
                message = update.get('message', {})
                chat = message.get('chat', {})
                
                # Проверяем наличие информации о теме
                thread_id = message.get('message_thread_id')
                topic_created = message.get('forum_topic_created')
                
                if topic_created and thread_id:
                    topic_name = topic_created.get('name', 'Без названия')
                    chat_id = chat.get('id')
                    
                    print(f"\nНайдена новая тема:")
                    print(f"ID чата: {chat_id}")
                    print(f"ID темы: {thread_id}")
                    print(f"Название: {topic_name}")
                    
                    # Сохраняем информацию о теме
                    save_topic(conn, chat_id, thread_id, topic_name)
            
            # Выводим все сохраненные темы
            cur = conn.cursor()
            cur.execute("SELECT * FROM forum_topics ORDER BY created_at DESC")
            topics = cur.fetchall()
            
            print("\nВсе сохраненные темы:")
            for topic in topics:
                print(f"ID темы: {topic[0]}, Название: {topic[2]}, Создана: {topic[3]}")
                
        else:
            print(f"Ошибка API: {data.get('description')}")
            
    except Exception as e:
        print(f"Ошибка при отслеживании тем: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    track_topics()
