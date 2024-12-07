import logging
import sys
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Добавляем корневую директорию в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.config import Config
from src.bot.handlers import start, help_command, handle_message
from src.utils.logger import setup_logger

def main():
    # Настройка логирования
    setup_logger()
    logger = logging.getLogger(__name__)
    
    # Загрузка конфигурации
    config = Config()
    
    # Инициализация бота
    application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    logger.info("Bot started")
    application.run_polling()

if __name__ == "__main__":
    main()
