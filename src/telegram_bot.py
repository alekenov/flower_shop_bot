import logging
import asyncio
import signal
import sys
import os
import fcntl
import time
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from services.sheets_service import SheetsService
from services.docs_service import DocsService
from services.config_service import ConfigService
from services.openai_service import OpenAIService

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SingleInstanceBot:
    """Ensure only one instance of the bot is running"""
    def __init__(self):
        self.lockfile = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot.lock')
        self.lockfd = None

    def acquire(self):
        """Try to acquire the lock"""
        try:
            if os.path.exists(self.lockfile):
                with open(self.lockfile, 'r') as f:
                    old_pid = f.read().strip()
                    try:
                        old_pid = int(old_pid)
                        logger.info(f"Attempting to terminate old process with PID {old_pid}")
                        os.kill(old_pid, signal.SIGTERM)
                        time.sleep(2)
                    except (ValueError, ProcessLookupError):
                        pass
            
            # Создаем новый файл блокировки
            self.lockfd = open(self.lockfile, 'w')
            fcntl.flock(self.lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lockfd.write(str(os.getpid()))
            self.lockfd.flush()
            return True
        except (IOError, OSError) as e:
            logger.error(f"Failed to acquire lock: {e}")
            if self.lockfd:
                self.lockfd.close()
            return False

    def release(self):
        """Release the lock"""
        try:
            if self.lockfd:
                fcntl.flock(self.lockfd, fcntl.LOCK_UN)
                self.lockfd.close()
                os.unlink(self.lockfile)
        except (IOError, OSError) as e:
            logger.error(f"Error releasing lock: {e}")

class TelegramBot:
    """Telegram bot for flower shop"""
    def __init__(self):
        """Initialize bot with necessary services"""
        self.config = ConfigService()
        self.sheets = SheetsService()
        self.docs = DocsService()
        self.openai = OpenAIService()
        self.token: Optional[str] = None
        self.application: Optional[Application] = None
        self.lock = SingleInstanceBot()

    async def get_bot_token(self):
        """Get bot token from database"""
        try:
            self.token = self.config.get_config('bot_token', service_name='telegram')
            if not self.token:
                raise ValueError("Telegram bot token not found in database")
        except Exception as e:
            logger.error(f"Failed to get bot token: {e}")
            raise

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        welcome_message = (
            "Привет! Я помощник цветочного магазина. "
            "Вы можете спросить меня о:\n"
            "- Наличии и ценах на цветы\n"
            "- Условиях доставки и самовывоза\n"
            "- Адресе и режиме работы\n"
            "Чем могу помочь?"
        )
        await update.message.reply_text(welcome_message)

    async def get_chat_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get chat ID"""
        await update.message.reply_text(f"Chat ID: {update.effective_chat.id}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages"""
        try:
            user_message = update.message.text.lower()
            user_id = update.effective_user.id
            logger.info(f"Получено сообщение от пользователя {user_id}: {user_message}")
            
            try:
                # Получаем ответ от OpenAI
                response = await self.openai.get_response(
                    user_message=user_message,
                    user_id=user_id
                )
                
                if not response:
                    response = "Извините, я не смог обработать ваш запрос. Попробуйте переформулировать вопрос."
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке сообщения: {str(e)}")
                response = "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже."

            logger.info(f"Отправляем ответ: {response}")
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error in handle_message: {str(e)}", exc_info=True)
            await update.message.reply_text(
                "Извините, произошла ошибка при обработке вашего сообщения. "
                "Пожалуйста, попробуйте позже."
            )

    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info("Received termination signal")
        self.lock.release()
        sys.exit(0)

    async def run(self):
        """Run the bot"""
        try:
            # Get bot token
            await self.get_bot_token()
            
            # Initialize bot
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.handle_start))
            self.application.add_handler(CommandHandler("chatid", self.get_chat_id))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Set up signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Acquire lock
            if not self.lock.acquire():
                logger.error("Another instance is already running")
                return
            
            logger.info("Starting bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Bot is ready to handle messages")
            
            # Keep the bot running
            stop_signal = asyncio.Event()
            await stop_signal.wait()
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            self.lock.release()
            raise

def main():
    """Main function"""
    bot = TelegramBot()
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
        raise
    finally:
        if bot.lock:
            bot.lock.release()

if __name__ == '__main__':
    main()
