import os
import logging
from typing import Optional
from src.utils.credentials_manager import credentials_manager

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        # Базовый путь проекта
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Определяем окружение
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
        
        # Загружаем учетные данные из базы данных
        self._load_credentials()

    def _load_credentials(self):
        """Загрузка всех необходимых учетных данных"""
        # Telegram
        telegram_creds = credentials_manager.get_credentials('telegram')
        # Выбираем токен в зависимости от окружения
        token_key = f'bot_token_{self.ENVIRONMENT}'
        self.TELEGRAM_BOT_TOKEN = telegram_creds.get(token_key) or telegram_creds.get('bot_token')
        self.TELEGRAM_LOG_CHANNEL_ID = telegram_creds.get('log_channel_id')
        
        if not self.TELEGRAM_BOT_TOKEN:
            raise ValueError(f"Telegram bot token not found for environment: {self.ENVIRONMENT}")
        
        # OpenAI
        openai_creds = credentials_manager.get_credentials('openai')
        self.OPENAI_API_KEY = openai_creds.get('api_key')
        self.OPENAI_MODEL = openai_creds.get('model', 'gpt-4-1106-preview')
        
        if not self.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found")
        
        # Google Sheets
        google_creds = credentials_manager.get_credentials('google')
        self.GOOGLE_SHEETS_SPREADSHEET_ID = google_creds.get('sheets_spreadsheet_id')
        self.GOOGLE_DOCS_KNOWLEDGE_BASE_ID = google_creds.get('docs_knowledge_base_id')
        self.GOOGLE_SERVICE_ACCOUNT = google_creds.get('service_account')
        
        if not self.GOOGLE_SHEETS_SPREADSHEET_ID:
            logger.warning("Credential not found: google.sheets_spreadsheet_id")
        if not self.GOOGLE_SERVICE_ACCOUNT:
            logger.warning("Credential not found: google.service_account")

    def get_credential(self, service: str, key: str) -> Optional[str]:
        """
        Получить значение учетных данных
        
        Args:
            service (str): Название сервиса (например, 'telegram', 'openai')
            key (str): Ключ учетных данных
            
        Returns:
            Optional[str]: Значение учетных данных или None, если не найдено
        """
        value = credentials_manager.get_credential(service, key)
        if value is None:
            logger.warning(f"Credential not found: {service}.{key}")
        return value
