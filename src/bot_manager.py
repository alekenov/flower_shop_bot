#!/usr/bin/env python3
import os
import sys
import signal
import psutil
import logging
import argparse
from telegram_bot import TelegramBot
from utils.logger_config import get_logger
from pathlib import Path

# Setup logging
logger = get_logger('bot_manager', logging.DEBUG)

# Константы
PID_FILE = Path(__file__).parent / "bot.pid"
LOG_FILE = Path(__file__).parent / "bot.log"

def read_pid():
    """Читаем PID из файла"""
    try:
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
    except Exception as e:
        logger.error(f"Ошибка при чтении PID файла: {e}")
    return None

def write_pid(pid):
    """Записываем PID в файл"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        logger.error(f"Ошибка при записи PID файла: {e}")

def is_running(pid):
    """Проверяем, запущен ли процесс"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def start_bot():
    """Запускаем бота"""
    # Проверяем, не запущен ли уже бот
    pid = read_pid()
    if pid and is_running(pid):
        logger.error(f"Бот уже запущен (PID: {pid})")
        return False

    # Очищаем старый PID файл
    if PID_FILE.exists():
        PID_FILE.unlink()

    try:
        # Запускаем бота в фоновом режиме
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path(__file__).parent)
        
        # Определяем режим работы
        is_prod = '--prod' in sys.argv
        env['ENVIRONMENT'] = 'prod' if is_prod else 'dev'
        
        with open(LOG_FILE, 'a') as log:
            process = subprocess.Popen(
                [sys.executable, '-c', 
                 'from telegram_bot import main; import asyncio; asyncio.run(main())'],
                stdout=log,
                stderr=log,
                env=env,
                start_new_session=True
            )

        # Записываем PID
        write_pid(process.pid)
        logger.info(f"Бот успешно запущен в режиме {'production' if is_prod else 'development'} (PID: {process.pid})")
        return True

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        return False

def stop_bot():
    """Останавливаем бота"""
    pid = read_pid()
    if not pid:
        logger.error("PID файл не найден")
        return False

    if not is_running(pid):
        logger.info("Бот не запущен")
        PID_FILE.unlink(missing_ok=True)
        return True

    try:
        # Отправляем SIGTERM
        os.kill(pid, signal.SIGTERM)
        
        # Ждем завершения процесса
        for _ in range(10):
            if not is_running(pid):
                break
            time.sleep(0.5)
        else:
            # Если процесс не завершился, отправляем SIGKILL
            os.kill(pid, signal.SIGKILL)
            logger.warning("Пришлось использовать SIGKILL для остановки бота")

        PID_FILE.unlink(missing_ok=True)
        logger.info(f"Бот остановлен (PID: {pid})")
        return True

    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")
        return False

def bot_status():
    """Проверяем статус бота"""
    pid = read_pid()
    if not pid:
        logger.info("Бот не запущен (PID файл не найден)")
        return False

    if is_running(pid):
        logger.info(f"Бот запущен (PID: {pid})")
        return True
    else:
        logger.info("Бот не запущен (процесс не найден)")
        PID_FILE.unlink(missing_ok=True)
        return False

def main():
    parser = argparse.ArgumentParser(description='Управление Telegram ботом')
    parser.add_argument('action', choices=['start', 'stop', 'status', 'restart'],
                       help='Действие для выполнения')
    parser.add_argument('--prod', action='store_true',
                       help='Запустить в production режиме (webhook)')
    args = parser.parse_args()

    if args.action == 'start':
        start_bot()
    elif args.action == 'stop':
        stop_bot()
    elif args.action == 'status':
        bot_status()
    elif args.action == 'restart':
        stop_bot()
        time.sleep(1)
        start_bot()

if __name__ == '__main__':
    main()
