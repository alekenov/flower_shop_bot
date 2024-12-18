import logging
from typing import Optional
from .credentials_service import credentials_service

logger = logging.getLogger(__name__)

class ConfigService:
    """Сервис для работы с конфигурацией"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigService, cls).__new__(cls)
        return cls._instance
    
    def get_config(self, key: str) -> Optional[str]:
        """
        Получение значения конфигурации по ключу
        
        Args:
            key: Ключ конфигурации в формате 'KEY' или 'SERVICE_KEY'
            
        Returns:
            Значение конфигурации или None, если не найдено
        """
        try:
            # Проверяем специальные ключи
            if key == 'TELEGRAM_BOT_TOKEN_DEV':
                return credentials_service.get_credential('telegram', 'bot_token_dev')
            elif key == 'TELEGRAM_BOT_TOKEN_PROD':
                return credentials_service.get_credential('telegram', 'bot_token_prod')
            elif key == 'OPENAI_API_KEY':
                return credentials_service.get_credential('openai', 'api_key')
                
            # Для остальных ключей пытаемся разобрать на сервис и ключ
            parts = key.lower().split('_', 1)
            if len(parts) != 2:
                logger.error(f"Invalid config key format: {key}")
                return None
                
            service_name, credential_key = parts
            
            # Получаем значение из credentials_service
            value = credentials_service.get_credential(service_name, credential_key)
            if value is None:
                logger.error(f"Config value not found for key: {key}")
            return value
            
        except Exception as e:
            logger.error(f"Error getting config for key {key}: {str(e)}")
            return None

# Создаем глобальный экземпляр сервиса
config_service = ConfigService()
