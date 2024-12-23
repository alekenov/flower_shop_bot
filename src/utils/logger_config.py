import logging
import os
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
from datetime import datetime

def setup_logger(name: str, log_level=logging.INFO):
    """
    Настройка логгера для работы с Cloud Logging
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    # Создаем форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Получаем или создаем логгер
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Очищаем существующие хендлеры
    if logger.handlers:
        logger.handlers.clear()
    
    # Создаем консольный хендлер (для локальной разработки)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # В Cloud Run добавляем Cloud Logging
    if os.getenv('K_SERVICE'):
        try:
            client = google.cloud.logging.Client()
            cloud_handler = CloudLoggingHandler(client, name=name)
            cloud_handler.setFormatter(formatter)
            logger.addHandler(cloud_handler)
            logger.info("Cloud Logging handler добавлен")
        except Exception as e:
            logger.error(f"Ошибка при настройке Cloud Logging: {e}")
    
    return logger

# Словарь для хранения уже созданных логгеров
loggers = {}

def get_logger(name: str, log_level=logging.INFO):
    """
    Получение логгера по имени
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования
        
    Returns:
        logging.Logger: Логгер
    """
    if name not in loggers:
        loggers[name] = setup_logger(name, log_level)
    return loggers[name]