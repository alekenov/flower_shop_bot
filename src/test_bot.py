import asyncio
import logging
from telegram import Bot
from services.config_service import ConfigService
from services.sheets_service import SheetsService

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

async def test_bot():
    """Test bot functionality"""
    try:
        # Инициализация сервисов
        config = ConfigService()
        sheets = SheetsService()
        
        # Получаем токен бота
        bot_token = config.get_config('bot_token', service_name='telegram')
        bot = Bot(token=bot_token)
        
        # Получаем chat_id для тестирования
        chat_id = config.get_config('test_chat_id', service_name='telegram')
        
        logger.info("Starting bot tests...")
        
        # Тест 1: Проверка подключения к боту
        me = await bot.get_me()
        logger.info(f"Bot info: {me.to_dict()}")
        
        # Тест 2: Проверка получения данных из Google Sheets
        inventory = sheets.get_inventory_data()
        logger.info(f"Retrieved inventory data: {inventory}")
        
        # Тест 3: Отправка тестовых сообщений
        test_messages = [
            "Что есть в наличии?",
            "Покажи доступные цветы",
            "Сколько стоят розы?",
            "/start"
        ]
        
        for msg in test_messages:
            logger.info(f"\nTesting message: {msg}")
            try:
                # Отправляем сообщение
                await bot.send_message(chat_id=chat_id, text=msg)
                logger.info(f"Successfully sent message: {msg}")
                
                # Ждем немного перед следующим сообщением
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error sending message '{msg}': {str(e)}")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
    finally:
        # Закрываем соединения
        if 'bot' in locals():
            await bot.close()

if __name__ == '__main__':
    asyncio.run(test_bot())
