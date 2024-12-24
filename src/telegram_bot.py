import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_output.log', mode='w', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

import asyncio
import signal
import sys
import os
import fcntl
import time
from typing import Optional
from aiohttp import web

from telegram import Update, Bot, CallbackQuery
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from services.sheets_service import SheetsService
from services.docs_service import DocsService
from services.config_service import ConfigService
from services.openai_service import OpenAIService
from services.feedback_service import FeedbackService

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
        self.log_group_id: Optional[str] = None
        self.feedback: Optional[FeedbackService] = None

    async def health_check(self, request):
        """Health check endpoint"""
        return web.Response(text='OK', status=200)
        
    async def webhook_handler(self, request):
        """Handle incoming webhook requests"""
        try:
            update = Update.de_json(await request.json(), self.application.bot)
            
            # Обработка callback query (нажатия на кнопки)
            if update.callback_query:
                await self.handle_callback_query(update, self.application)
            # Обработка сообщений
            elif update.message:
                await self.handle_message(update, self.application)
            
            return web.Response(status=200)
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return web.Response(status=500)

    async def get_bot_token(self):
        """Get bot token from database"""
        try:
            logger.info("Getting bot token from database")
            self.token = await self.config.get_config_async('bot_token_dev', service='telegram')
            if not self.token:
                raise ValueError("Bot token not found in database")
            logger.info("Successfully got bot token")
        except Exception as e:
            logger.error(f"Failed to get bot token: {e}")
            sys.exit(1)

    async def get_log_group_id(self):
        """Get log group ID from database"""
        try:
            self.log_group_id = await self.config.get_config_async('log_group_id', service='telegram')
            logger.info(f"Log group ID loaded: {self.log_group_id}")
        except Exception as e:
            logger.error(f"Error loading log group ID: {e}")
            raise

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        await update.message.reply_text(f'Здравствуйте, {user.first_name}! Я помогу вам с заказом цветов.')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages"""
        try:
            message = update.message
            if not message or not message.text:
                return

            text = message.text
            user = message.from_user
            
            logger.info(
                "\n=== НОВОЕ СООБЩЕНИЕ ===\n"
                f"От: {user.first_name} ({user.id})\n"
                f"Текст: {text}\n"
                "======================="
            )
                
            # Если это личное сообщение боту
            if message.chat.type == 'private':
                # Получаем ответ из документов/таблиц с использованием кэша
                logger.info("\n=== ПОЛУЧЕНИЕ ДАННЫХ ИНВЕНТАРЯ ===")
                inventory_data = await self.sheets.get_inventory_data()
                logger.info(f"Получено товаров: {len(inventory_data) if inventory_data else 0}")
                
                # Получаем релевантные знания и ответ
                logger.info("\n=== ПОИСК РЕЛЕВАНТНЫХ ЗНАНИЙ ===")
                relevant_knowledge = await self.docs.get_relevant_knowledge(text)
                logger.info(f"Найденные знания:\n{relevant_knowledge}")
                
                logger.info("\n=== ГЕНЕРАЦИЯ ОТВЕТА ===")
                response = await self.docs.get_response(text, inventory_data)
                logger.info(f"Ответ бота:\n{response}")
                
                await message.reply_text(response)
                
                # Логируем сообщение в группе
                log_message = (
                    f"*Новое сообщение от клиента*\n\n"
                    f"👤 *Пользователь*:\n"
                    f"ID: `{user.id}`\n"
                    f"Имя: {user.first_name} {user.last_name if user.last_name else ''}\n"
                    f"Username: @{user.username if user.username else 'Нет'}\n\n"
                    f"❓ *Вопрос*:\n{text}\n\n"
                    f"📚 *Использованные знания*:\n{relevant_knowledge}\n\n"
                    f"✍️ *Ответ бота*:\n{response}"
                )
                
                # Получаем ID темы для логов
                logs_topic_id = await self.feedback.get_topic_id('📝 Логи')
                
                log_msg = await context.bot.send_message(
                    chat_id=self.log_group_id,
                    message_thread_id=logs_topic_id,
                    text=log_message,
                    parse_mode="Markdown"
                )
                
                # Добавляем кнопки для оценки к логу
                await self.feedback.add_feedback_buttons(
                    chat_id=self.log_group_id,
                    topic_id=logs_topic_id,
                    message_id=log_msg.message_id
                )
                
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await message.reply_text("Извините, произошла ошибка. Попробуйте позже.")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает нажатия на кнопки"""
        query = update.callback_query
        data = query.data
        message = query.message
        chat_id = str(message.chat_id)
        message_id = message.message_id

        try:
            action, topic_id_str, orig_message_id_str = data.split("_")
            
            # Проверяем и конвертируем topic_id
            try:
                topic_id = int(topic_id_str) if topic_id_str != 'None' else None
            except ValueError:
                logger.error(f"Некорректный topic_id: {topic_id_str}")
                await query.answer(text="Ошибка: некорректный ID темы")
                return
                
            # Проверяем и конвертируем orig_message_id
            try:
                orig_message_id = int(orig_message_id_str)
            except ValueError:
                logger.error(f"Некорректный message_id: {orig_message_id_str}")
                await query.answer(text="Ошибка: некорректный ID сообщения")
                return

            if action == "dislike":
                success, response_text = await self.feedback.handle_dislike(chat_id, orig_message_id, topic_id)
                if success:
                    await self.feedback.update_message_buttons(chat_id, message_id, topic_id, "dislike")
            
            elif action == "like":
                success, response_text = await self.feedback.handle_like(chat_id, orig_message_id, topic_id)
                if success:
                    await self.feedback.update_message_buttons(chat_id, message_id, topic_id, "like")
            
            elif action in ("liked", "done"):
                response_text = "Вы уже оценили это сообщение"
            
            else:
                response_text = "Неизвестное действие"

            await query.answer(text=response_text)
        except ValueError as e:
            logger.error(f"Ошибка при разборе callback query данных: {str(e)}")
            await query.answer(text="Ошибка при обработке")
        except Exception as e:
            logger.error(f"Ошибка при обработке callback query: {str(e)}")
            await query.answer(text="Произошла ошибка при обработке")

    async def handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /update command"""
        # Проверяем, что команда пришла от оператора
        if update.effective_chat.type != 'private':
            return
            
        # Проверяем, является ли пользователь оператором
        is_operator = await self.config.get_config_async('operators', service='telegram')
        if not is_operator or str(update.effective_user.id) not in is_operator.split(','):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
            return

        # Обновляем данные
        success = await self.sheets.update_data()
        
        if success:
            await update.message.reply_text("✅ Данные успешно обновлены")
        else:
            await update.message.reply_text("❌ Ошибка при обновлении данных")

    def signal_handler(self, signum, frame):
        """Handle termination signals"""
        logger.info("Received termination signal")
        self.lock.release()
        sys.exit(0)

    async def setup_application(self):
        """Setup bot application"""
        try:
            # Get bot token
            await self.get_bot_token()
            
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Get log group ID
            await self.get_log_group_id()
            
            # Initialize feedback service
            self.feedback = FeedbackService(self.application.bot)
            await self.feedback.initialize()
            
            # Setup handlers
            self.setup_handlers()
            
            logger.info("Bot application setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup application: {e}")
            raise

    async def setup_handlers(self):
        """Setup message handlers"""
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("update", self.handle_update))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback_query))

    async def run(self):
        """Run the bot"""
        if not self.lock.acquire():
            logger.warning("Bot is already running")
            return

        try:
            await self.get_bot_token()
            await self.get_log_group_id()
            
            # Initialize services
            self.sheets = SheetsService()
            await self.sheets.initialize()
            
            # Initialize bot and services
            bot = Bot(token=self.token)
            self.feedback = FeedbackService(bot)
            await self.feedback.initialize()
            
            # Create application
            self.application = Application.builder().bot(bot).build()
            
            # Setup handlers
            await self.setup_handlers()
            
            # Start polling
            logger.info("Starting bot in polling mode...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Keep the bot running
            try:
                while True:
                    await asyncio.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                logger.info("Stopping bot...")
            
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            self.lock.release()
            raise
        finally:
            # Properly shut down
            try:
                if self.application:
                    await self.application.updater.stop()
                    await self.application.stop()
                    await self.application.shutdown()
                    logger.info("Bot stopped successfully")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
            finally:
                self.lock.release()

if __name__ == '__main__':
    try:
        bot = TelegramBot()
        asyncio.run(bot.run())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {str(e)}", exc_info=True)
        sys.exit(1)
