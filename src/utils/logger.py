import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    Настройка логирования для приложения
    """
    # Создаем логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Форматирование логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Хендлер для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Хендлер для файла
    file_handler = RotatingFileHandler(
        'bot.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Отключаем логи от библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
