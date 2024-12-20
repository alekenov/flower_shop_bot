import os
import logging
from typing import Optional, Dict
from src.utils.credentials_manager import credentials_manager

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        """Инициализация конфигурации"""
        # Базовый путь проекта
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Определяем окружение
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
        
        # Кэш для учетных данных
        self._credentials_cache: Dict[str, Dict[str, str]] = {}
        
        # Загружаем основные учетные данные
        self._init_required_credentials()
    
    def _get_service_credentials(self, service: str) -> Dict[str, str]:
        """
        Получение учетных данных сервиса с кэшированием
        
        Args:
            service: Название сервиса
            
        Returns:
            Dict[str, str]: Словарь с учетными данными
        """
        if service not in self._credentials_cache:
            self._credentials_cache[service] = credentials_manager.get_credentials(service)
        return self._credentials_cache[service]
    
    def _init_required_credentials(self):
        """Инициализация обязательных учетных данных"""
        # Telegram
        telegram_creds = self._get_service_credentials('telegram')
        token_key = f'bot_token_{self.ENVIRONMENT}'
        self.TELEGRAM_BOT_TOKEN = telegram_creds.get(token_key) or telegram_creds.get('bot_token')
        
        if not self.TELEGRAM_BOT_TOKEN:
            raise ValueError(f"Telegram bot token not found for environment: {self.ENVIRONMENT}")
        
        # OpenAI
        openai_creds = self._get_service_credentials('openai')
        self.OPENAI_API_KEY = openai_creds.get('api_key')
        
        if not self.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found")
    
    def get_credential(self, service: str, key: str, required: bool = False) -> Optional[str]:
        """
        Получение значения учетных данных
        
        Args:
            service: Название сервиса
            key: Ключ учетных данных
            required: Является ли значение обязательным
            
        Returns:
            Optional[str]: Значение учетных данных
            
        Raises:
            ValueError: Если required=True и значение не найдено
        """
        creds = self._get_service_credentials(service)
        value = creds.get(key)
        
        if value is None:
            msg = f"Credential not found: {service}.{key}"
            if required:
                raise ValueError(msg)
            logger.warning(msg)
        
        return value
    
    @property
    def OPENAI_MODEL(self) -> str:
        """Модель OpenAI для использования"""
        return self.get_credential('openai', 'model') or 'gpt-4-1106-preview'
    
    @property
    def GOOGLE_SHEETS_SPREADSHEET_ID(self) -> Optional[str]:
        """ID таблицы Google Sheets"""
        return self.get_credential('google', 'sheets_spreadsheet_id')
    
    @property
    def GOOGLE_DOCS_KNOWLEDGE_BASE_ID(self) -> Optional[str]:
        """ID документа базы знаний Google Docs"""
        return self.get_credential('google', 'docs_knowledge_base_id')
    
    @property
    def GOOGLE_SERVICE_ACCOUNT(self) -> Optional[str]:
        """Учетные данные сервисного аккаунта Google"""
        return self.get_credential('google', 'service_account')
    
    @property
    def TELEGRAM_LOG_CHANNEL_ID(self) -> Optional[str]:
        """ID канала для логирования в Telegram"""
        return self.get_credential('telegram', 'log_channel_id')
