import sys
import os
import requests
import logging

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.credentials_service import credentials_service

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def set_webhook(webhook_url: str):
    """
    Устанавливает webhook для Telegram бота
    
    Args:
        webhook_url: URL для webhook
    """
    try:
        # Получаем токен бота из credentials service
        bot_token = credentials_service.get_credential('telegram', 'bot_token_prod')
        if not bot_token:
            raise ValueError("Bot token not found in credentials")
            
        # Формируем URL для установки webhook
        api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        
        # Отправляем запрос
        response = requests.post(api_url, json={'url': webhook_url})
        response.raise_for_status()
        
        # Проверяем ответ
        result = response.json()
        if result.get('ok'):
            logger.info(f"Webhook successfully set to: {webhook_url}")
        else:
            logger.error(f"Failed to set webhook: {result.get('description')}")
            
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        raise

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python set_webhook.py <webhook_url>")
        sys.exit(1)
        
    webhook_url = sys.argv[1]
    set_webhook(webhook_url)
