import os
import logging
from services.sheets_service import GoogleSheetsService

# Настройка логирования
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sheets_connection():
    try:
        # Создаем экземпляр сервиса
        sheets_service = GoogleSheetsService()
        
        # Тестируем запись
        sheets_service.log_conversation(
            user_id=12345,
            user_message="Test message",
            bot_response="Test response"
        )
        
        # Тестируем чтение статистики
        stats = sheets_service.get_statistics()
        print("Statistics:", stats)
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise

if __name__ == "__main__":
    test_sheets_connection()
