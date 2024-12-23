import logging
import asyncio
import signal
import sys
import os
import fcntl
import time
from typing import Optional
from aiohttp import web

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
            logger.error(f"Could not acquire lock: {e}")
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
        
    async def health_check(self, request):
        """Health check endpoint"""
        return web.Response(text='OK', status=200)
        
    async def webhook_handler(self, request):
        """Handle incoming webhook requests"""
        try:
            update = Update.de_json(await request.json(), self.application.bot)
            await self.application.process_update(update)
            return web.Response(status=200)
        except Exception as e:
            logger.error(f"Error processing update: {e}")
            return web.Response(status=500)

    async def get_bot_token(self):
        """Get bot token from database"""
        try:
            self.token = await self.config.get_config_async('TELEGRAM_BOT_TOKEN_DEV', service='telegram')
            if not self.token:
                raise ValueError("Bot token not found in database")
        except Exception as e:
            logger.error(f"Failed to get bot token: {e}")
            sys.exit(1)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        await update.message.reply_text(f'Здравствуйте, {user.first_name}! Я помогу вам с заказом цветов.')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            user_message = update.message.text
            response = await self.openai.get_response(user_message)
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("Извините, произошла ошибка. Попробуйте позже.")

    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info("Received termination signal")
        self.lock.release()
        sys.exit(0)

    async def setup_application(self):
        """Setup bot application"""
        await self.get_bot_token()
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Setup webhook
        webhook_url = "https://flower-shop-bot-315649427788.europe-west1.run.app/webhook"
        webhook_secret = await self.config.get_config_async('TELEGRAM_WEBHOOK_SECRET')
        await self.application.bot.set_webhook(
            url=webhook_url,
            secret_token=webhook_secret
        )
        
        # Setup web application
        app = web.Application()
        app.router.add_get('/health', self.health_check)
        app.router.add_post('/webhook', self.webhook_handler)
        
        return app

    async def run(self):
        """Run the bot"""
        if not self.lock.acquire():
            logger.error("Another instance is already running")
            sys.exit(1)

        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        try:
            app = await self.setup_application()
            port = int(os.environ.get('PORT', 8000))
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            
            logger.info(f"Bot started on port {port}")
            
            # Keep the application running
            while True:
                await asyncio.sleep(3600)
                
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            self.lock.release()
            sys.exit(1)

async def main():
    """Main function"""
    bot = TelegramBot()
    await bot.run()

if __name__ == '__main__':
    asyncio.run(main())
