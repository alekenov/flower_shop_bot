import asyncio
import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.services.sheets_service import SheetsService
from src.services.openai_service import OpenAIService

# Настройка логирования
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_inventory():
    try:
        # Инициализируем сервисы
        sheets_service = SheetsService()
        openai_service = OpenAIService()
        
        # Получаем данные из Google Sheets
        inventory_data = await sheets_service.get_inventory_data()
        logger.info(f"Retrieved inventory data: {inventory_data}")
        
        # Форматируем данные для OpenAI
        inventory_info = sheets_service.format_inventory_for_openai(inventory_data)
        logger.info(f"Formatted inventory info: {inventory_info}")
        
        # Тестовые запросы
        test_questions = [
            "Сколько стоят красные розы?",
            "Есть ли в наличии тюльпаны?",
            "Хочу купить букет из хризантем"
        ]
        
        # Получаем и проверяем ответы
        for question in test_questions:
            logger.info(f"\nTesting question: {question}")
            response = await openai_service.get_response(question, inventory_info)
            logger.info(f"Response: {response}")
            
        logger.info("All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(test_inventory())
