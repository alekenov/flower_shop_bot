import requests
import psycopg2
from psycopg2.extras import DictCursor
import json
from datetime import datetime

def get_forum_topics():
    # Получаем токен бота из базы данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT credential_value FROM credentials WHERE service_name = 'telegram' AND credential_key = 'bot_token'")
    bot_token = cur.fetchone()['credential_value']
    
    # URL для получения обновлений
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        # Получаем обновления с максимальным лимитом
        params = {
            'limit': 100,
            'allowed_updates': ['message']
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('ok'):
            updates = data['result']
            topics = {}  # словарь для хранения информации о темах
            
            for update in updates:
                message = update.get('message', {})
                
                # Проверяем наличие информации о создании темы в reply_to_message
                reply = message.get('reply_to_message', {})
                topic_created = reply.get('forum_topic_created')
                
                if topic_created:
                    thread_id = reply.get('message_thread_id')
                    if thread_id and thread_id not in topics:
                        topics[thread_id] = {
                            'name': topic_created.get('name'),
                            'created_date': datetime.fromtimestamp(reply.get('date', 0)),
                            'icon_color': topic_created.get('icon_color'),
                            'icon_emoji': topic_created.get('icon_custom_emoji_id')
                        }
            
            # Выводим информацию о найденных темах
            print(f"\nНайдено тем: {len(topics)}")
            for thread_id, topic_info in topics.items():
                print(f"\nТема:")
                print(f"ID: {thread_id}")
                print(f"Название: {topic_info['name']}")
                print(f"Создана: {topic_info['created_date']}")
                if topic_info['icon_color']:
                    print(f"Цвет иконки: {topic_info['icon_color']}")
                if topic_info['icon_emoji']:
                    print(f"Emoji ID: {topic_info['icon_emoji']}")
                print("-" * 30)
        
        else:
            print(f"Ошибка API: {data.get('description')}")
            
    except Exception as e:
        print(f"Ошибка при получении тем форума: {str(e)}")
    finally:
        conn.close()

if __name__ == '__main__':
    get_forum_topics()
