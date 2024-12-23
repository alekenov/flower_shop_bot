import asyncio
from telegram import Bot
import psycopg2
from psycopg2.extras import DictCursor

async def get_forum_topics():
    # Получаем токен бота из базы данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("SELECT credential_value FROM credentials WHERE service_name = 'telegram' AND credential_key = 'bot_token'")
    bot_token = cur.fetchone()['credential_value']
    
    # Создаем экземпляр бота
    bot = Bot(token=bot_token)
    
    try:
        # ID группы "Цветы"
        chat_id = -1001375195020
        
        # Получаем список тем форума
        forum_topics = await bot.get_forum_topics(chat_id)
        
        print("\nСписок тем в группе:")
        if forum_topics:
            for topic in forum_topics:
                print(f"\nID темы: {topic.message_thread_id}")
                print(f"Название: {topic.name}")
                print(f"Иконка: {topic.icon_custom_emoji_id if topic.icon_custom_emoji_id else 'Нет'}")
        else:
            print("Темы не найдены")
            
    except Exception as e:
        print(f"Ошибка при получении тем форума: {str(e)}")

if __name__ == '__main__':
    asyncio.run(get_forum_topics())
