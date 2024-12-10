import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Загружаем переменные окружения из .env файла
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            '.env'
        )
        load_dotenv(env_path)
        
        # Базовый путь проекта
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Telegram
        self.TELEGRAM_BOT_TOKEN = self._get_env('TELEGRAM_BOT_TOKEN')
        self.TELEGRAM_LOG_CHANNEL_ID = self._get_env('TELEGRAM_LOG_CHANNEL_ID')
        
        # OpenAI
        self.OPENAI_API_KEY = self._get_env('OPENAI_API_KEY')
        
        # Google Sheets
        self.GOOGLE_SHEETS_SPREADSHEET_ID = self._get_env('GOOGLE_SHEETS_SPREADSHEET_ID')
        self.GOOGLE_DOCS_KNOWLEDGE_BASE_ID = self._get_env('GOOGLE_DOCS_KNOWLEDGE_BASE_ID')

    def _get_env(self, key: str) -> str:
        """
        Получает значение переменной окружения
        Вызывает исключение, если переменная не найдена
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Environment variable {key} is not set")
        return value
