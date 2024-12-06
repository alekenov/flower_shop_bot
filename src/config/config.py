import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Загружаем переменные окружения из .env файла
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            '.env.example'
        )
        load_dotenv(env_path)
        
        # Базовый путь проекта
        self.PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Telegram
        self.TELEGRAM_BOT_TOKEN = self._get_env('TELEGRAM_BOT_TOKEN')
        
        # OpenAI
        self.OPENAI_API_KEY = self._get_env('OPENAI_API_KEY')
        
        # Google Sheets
        self.GOOGLE_SHEETS_CREDENTIALS_FILE = os.path.join(
            self.PROJECT_ROOT,
            'src/config/credentials/google_sheets_credentials.json'
        )
        self.GOOGLE_SHEETS_SPREADSHEET_ID = '1KIjFJppiwHXikFQrWz_7vKyDykA6LZ09rMH5-qIFBQk'

        # Google Docs Knowledge Base
        self.GOOGLE_DOCS_KNOWLEDGE_BASE_ID = '1KsRZZ1I2E45uXrRjYlwnwzCPM5faio6ohvjdgbnQExo'

    def _get_env(self, key: str) -> str:
        """
        Получает значение переменной окружения
        Вызывает исключение, если переменная не найдена
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Environment variable {key} is not set")
        return value
