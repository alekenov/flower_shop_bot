import sys
import os

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.utils.credentials_manager import credentials_manager

def update_tokens():
    # Сохраняем тестовый токен с ключом bot_token_dev
    credentials_manager.set_credential(
        'telegram', 
        'bot_token_dev',
        '432633449:AAE-f7hO9fbfoBXGH9bTs0-O0-PEg1MlyQQ',
        'Development Telegram bot token'
    )
    
    print("Bot tokens updated successfully")

if __name__ == '__main__':
    update_tokens()
