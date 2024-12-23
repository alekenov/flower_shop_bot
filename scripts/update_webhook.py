#!/usr/bin/env python3
import os
import sys
import requests
import logging

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.config_service import config_service

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_webhook():
    """Обновить URL вебхука в Telegram"""
    try:
        # Получаем токен бота
        bot_token = config_service.get_config('TELEGRAM_BOT_TOKEN_PROD')
        if not bot_token:
            raise ValueError("Bot token not found in database")
            
        # Получаем секретный токен для вебхука
        webhook_secret = config_service.get_config('TELEGRAM_WEBHOOK_SECRET')
        if not webhook_secret:
            raise ValueError("Webhook secret not found in database")
            
        # URL вебхука в Supabase
        webhook_url = f"https://dkohweivbdwweyvyvcbc.supabase.co/functions/v1/telegram-webhook/{bot_token}"
        
        # Параметры для установки вебхука
        params = {
            'url': webhook_url,
            'secret_token': webhook_secret,
            'drop_pending_updates': True  # Опционально: пропустить накопившиеся обновления
        }
        
        # URL для установки вебхука
        api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        
        logger.info(f"Setting webhook URL to: {webhook_url}")
        response = requests.post(api_url, json=params)
        response.raise_for_status()
        
        result = response.json()
        if result.get('ok'):
            logger.info("Webhook successfully set!")
            logger.info(f"Response: {result}")
            
            # Проверяем текущие настройки вебхука
            info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            info_response = requests.get(info_url)
            info_response.raise_for_status()
            
            webhook_info = info_response.json()
            logger.info(f"Current webhook info: {webhook_info}")
        else:
            raise ValueError(f"Failed to set webhook: {result}")
            
    except Exception as e:
        logger.error(f"Error updating webhook: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        update_webhook()
        print("\nWebhook successfully updated!")
    except Exception as e:
        print(f"\nFailed to update webhook: {str(e)}")
        sys.exit(1)
