import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Загружаем переменные окружения из .env файла
        load_dotenv()
        
        # Telegram
        self.TELEGRAM_BOT_TOKEN = self._get_env('TELEGRAM_BOT_TOKEN')
        
        # OpenAI
        self.OPENAI_API_KEY = self._get_env('OPENAI_API_KEY')
        
        # Google Sheets
        self.GOOGLE_SHEETS_CREDENTIALS_FILE = self._get_env('GOOGLE_SHEETS_CREDENTIALS_FILE')
        self.GOOGLE_SHEETS_SPREADSHEET_ID = self._get_env('GOOGLE_SHEETS_SPREADSHEET_ID')

    def _get_env(self, key: str) -> str:
        """
        Получает значение переменной окружения
        Вызывает исключение, если переменная не найдена
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Environment variable {key} is not set")
        return value
