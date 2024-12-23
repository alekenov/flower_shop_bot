import requests
import psycopg2
from psycopg2.extras import DictCursor
import json

def get_forum_topics():
    # Получаем токен бота из базы данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT credential_value FROM credentials WHERE service_name = 'telegram' AND credential_key = 'bot_token'")
    bot_token = cur.fetchone()['credential_value']
    
    # ID группы "Цветы"
    chat_id = -1001375195020
    
    # URL для получения тем форума
    url = f"https://api.telegram.org/bot{bot_token}/getForumTopicsByChat"
    
    try:
        # Делаем запрос к API
        response = requests.get(url, params={'chat_id': chat_id})
        data = response.json()
        
        print("\nОтвет API:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if data.get('ok'):
            topics = data.get('result', [])
            print("\nСписок тем в группе:")
            for topic in topics:
                print(f"\nID темы: {topic.get('message_thread_id')}")
                print(f"Название: {topic.get('name')}")
                if topic.get('icon_custom_emoji_id'):
                    print(f"Иконка: {topic['icon_custom_emoji_id']}")
        else:
            print(f"\nОшибка API: {data.get('description')}")
            
    except Exception as e:
        print(f"Ошибка при получении тем форума: {str(e)}")

if __name__ == '__main__':
    get_forum_topics()
