import os
import json
import logging
import asyncio
import re
from typing import Dict, List, Optional
from datetime import datetime
import signal

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from function_handlers import TOOL_DEFINITIONS, execute_function
from services.config_service import config_service

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Системные сообщения для разных языков
SYSTEM_MESSAGES = {
    "ru": """Вы - помощник цветочного магазина Cvety.kz. Помогайте клиентам с:
    - Выбором и заказом цветов и букетов
    - Оформлением доставки
    - Отслеживанием статуса заказа
    - Подтверждением фото букета
    - Обработкой возвратов
    Общайтесь вежливо и профессионально. Используйте предоставленные инструменты для помощи клиентам.""",
    
    "kk": """Сіз Cvety.kz гүл дүкенінің көмекшісіз. Клиенттерге көмектесіңіз:
    - Гүлдер мен букеттерді таңдау және тапсырыс беру
    - Жеткізуді рәсімдеу
    - Тапсырыс күйін бақылау
    - Букет фотосын растау
    - Қайтаруды өңдеу
    Сыпайы және кәсіби түрде қарым-қатынас жасаңыз. Клиенттерге көмектесу үшін берілген құралдарды пайдаланыңыз.""",
    
    "en": """You are a Cvety.kz flower shop assistant. Help customers with:
    - Selecting and ordering flowers and bouquets
    - Arranging delivery
    - Tracking order status
    - Confirming bouquet photos
    - Processing returns
    Communicate politely and professionally. Use the provided tools to assist customers."""
}

class FlowerShopBot:
    def __init__(self):
        """Initialize bot with application instance"""
        self.is_running = False
        
        # Initialize OpenAI client
        self.openai_api_key = config_service.get_config('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found in database")
        self.client = AsyncOpenAI(api_key=self.openai_api_key)

        # Get bot token
        self.bot_token = config_service.get_config('TELEGRAM_BOT_TOKEN_DEV')
        if not self.bot_token:
            raise ValueError("Development Telegram bot token not found in database")

        # Initialize application
        self.application = Application.builder().token(self.bot_token).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup message handlers"""
        logger.info("Setting up message handlers")
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        logger.info("Message handlers setup completed")
        
    @staticmethod
    async def detect_language(text: str) -> str:
        """Определить язык сообщения"""
        # Простая проверка на наличие кириллицы
        has_cyrillic = bool(re.search('[а-яА-Я]', text))
        
        if not has_cyrillic:
            return "en"
        
        # Проверка на казахские специфичные буквы
        has_kazakh = bool(re.search('[әіңғүұқөһ]', text.lower()))
        
        return "kk" if has_kazakh else "ru"
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Отправка приветственного сообщения при команде /start"""
        try:
            # Определяем язык пользователя
            lang = "ru"  # По умолчанию русский
            if update.message.from_user.language_code:
                if update.message.from_user.language_code.startswith('kk'):
                    lang = "kk"
                elif update.message.from_user.language_code.startswith('en'):
                    lang = "en"
            
            # Приветственные сообщения на разных языках
            welcome_messages = {
                "ru": """Здравствуйте! Я помощник цветочного магазина Cvety.kz. 
Я помогу вам:
- Выбрать и заказать цветы
- Оформить доставку
- Отследить статус заказа
- Подтвердить фото букета
- Обработать возврат

Чем могу помочь?""",
                
                "kk": """Сәлеметсіз бе! Мен Cvety.kz гүл дүкенінің көмекшісімін.
Мен сізге көмектесемін:
- Гүлдерді таңдау және тапсырыс беру
- Жеткізуді рәсімдеу
- Тапсырыс күйін бақылау
- Букет фотосын растау
- Қайтаруды өңдеу

Немен көмектесе аламын?""",
                
                "en": """Hello! I'm the Cvety.kz flower shop assistant.
I can help you:
- Select and order flowers
- Arrange delivery
- Track order status
- Confirm bouquet photos
- Process returns

How can I assist you?"""
            }
            
            # Отправляем приветственное сообщение
            await update.message.reply_text(welcome_messages[lang])
            
            # Инициализируем историю сообщений
            context.user_data['messages'] = [{"role": "system", "content": SYSTEM_MESSAGES[lang]}]
            context.user_data['current_lang'] = lang
            
        except Exception as e:
            logger.error(f"Error in start command: {str(e)}", exc_info=True)
            await update.message.reply_text("An error occurred. Please try again later.")
            
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка входящих сообщений"""
        try:
            # Получаем текст сообщения
            text = update.message.text
            logger.info(f"Received message: {text}")
            
            # Отправляем индикатор набора текста
            await update.message.chat.send_chat_action(action="typing")
            logger.info("Sent typing action")

            # Определяем язык сообщения
            lang = await self.detect_language(text)
            logger.info(f"Detected language: {lang}")

            # История сообщений пользователя
            if 'messages' not in context.user_data:
                logger.info("Initializing message history")
                context.user_data['messages'] = []
                context.user_data['current_lang'] = lang
            
            # Добавляем системное сообщение, если это первое сообщение или язык изменился
            if (not context.user_data['messages'] or 
                context.user_data['current_lang'] != lang):
                logger.info(f"Setting system message for language: {lang}")
                context.user_data['messages'] = [{"role": "system", "content": SYSTEM_MESSAGES[lang]}]
                context.user_data['current_lang'] = lang

            # Добавляем сообщение пользователя
            context.user_data['messages'].append({"role": "user", "content": text})
            logger.info("Added user message to history")
            
            try:
                # Получаем ответ от OpenAI
                logger.info("Requesting OpenAI response")
                response = await self.get_openai_response(context.user_data['messages'])
                logger.info(f"OpenAI response received: {response}")
                
                # Добавляем ответ ассистента в историю
                context.user_data['messages'].append({"role": "assistant", "content": response})
                logger.info("Added assistant response to history")
                
                # Отправляем ответ пользователю
                await update.message.reply_text(response)
                logger.info("Sent response to user")
                
            except Exception as e:
                logger.error(f"Error in OpenAI communication: {str(e)}", exc_info=True)
                error_messages = {
                    "ru": "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или переформулируйте ваш вопрос.",
                    "kk": "Кешіріңіз, сұрауыңызды өңдеу кезінде қате пайда болды. Қайталап көріңіз немесе сұрағыңызды басқаша тұжырымдаңыз.",
                    "en": "Sorry, there was an error processing your request. Please try again or rephrase your question."
                }
                await update.message.reply_text(error_messages[lang])
                
        except Exception as e:
            logger.error(f"Error in message handling: {str(e)}", exc_info=True)
            await update.message.reply_text("An unexpected error occurred. Please try again later.")
            
    async def get_openai_response(self, messages: List[Dict]) -> str:
        """Получение ответа от OpenAI API"""
        try:
            logger.debug(f"Messages: {messages}")
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto"
            )
            
            logger.info("Received response from OpenAI")
            logger.debug(f"Response: {response}")
            
            # Обработка ответа
            if response.choices[0].message.tool_calls:
                # Если есть вызовы инструментов
                tool_calls = response.choices[0].message.tool_calls
                
                # Добавляем сообщение ассистента с вызовами функций
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in tool_calls]
                })
                
                # Выполняем все функции и собираем их результаты
                for tool_call in tool_calls:
                    try:
                        # Выполнение функции
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        logger.info(f"Executing function: {function_name}")
                        logger.debug(f"Arguments: {function_args}")
                        
                        function_response = await execute_function(function_name, function_args)
                        logger.info(f"Function response received: {function_response}")
                        
                        # Добавляем результат выполнения функции
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(function_response)
                        })
                        
                    except Exception as e:
                        logger.error(f"Error executing function {function_name}: {str(e)}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps({"error": str(e)})
                        })
                
                # Получаем финальный ответ от OpenAI с учетом результатов выполнения функций
                final_response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages
                )
                
                return final_response.choices[0].message.content
            else:
                # Если нет вызовов инструментов, возвращаем прямой ответ
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error in OpenAI communication: {str(e)}", exc_info=True)
            raise
            
    async def stop(self):
        """Stop the bot gracefully"""
        if self.is_running:
            logger.info("Stopping bot...")
            self.is_running = False
            if self.application.updater:
                await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Bot stopped")
            
    async def run(self):
        """Run the bot"""
        try:
            if not self.is_running:
                self.is_running = True
                logger.info("Starting bot...")
                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling(drop_pending_updates=True)
                logger.info("Bot is running...")
                
                # Keep the bot running until stop() is called
                while self.is_running:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Error in polling: {str(e)}")
            raise
        finally:
            await self.stop()

def handle_signals():
    """Setup signal handlers"""
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received stop signal")
        if bot and bot.is_running:
            loop.create_task(bot.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

async def main():
    """Main function to run the bot"""
    global bot
    try:
        bot = FlowerShopBot()
        handle_signals()
        await bot.run()
    except Exception as e:
        logger.error(f"Bot stopped due to error: {str(e)}")
        if bot:
            await bot.stop()
        raise

if __name__ == '__main__':
    bot = None
    asyncio.run(main())
