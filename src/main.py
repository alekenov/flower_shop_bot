import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from src.config.config import Config
from src.bot.handlers import start, help_command, handle_message, get_channel_id
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
    application.add_handler(CommandHandler("channel_id", get_channel_id))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    logger.info("Bot started")
    application.run_polling()

if __name__ == "__main__":
    main()
