import os
import json
import logging
import asyncio
import re
import time
from typing import Dict, List, Optional
from datetime import datetime
import signal

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from function_handlers import TOOL_DEFINITIONS, execute_function
from services.config_service import config_service
from services.cache_service import CacheService

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Системные сообщения для разных языков
SYSTEM_MESSAGES = {
    "ru": """Вы - дружелюбный консультант цветочного магазина Cvety.kz. Общайтесь с клиентами тепло и естественно, как опытный продавец цветов.

Ваш стиль общения:
- Говорите просто и понятно, без формальностей
- Всегда обращайтесь к клиентам на "Вы"
- Не выдавайте сразу всю информацию, если не спрашивают
- Задавайте уточняющие вопросы, чтобы лучше понять потребности клиента

Как отвечать на типичные вопросы:
- На "Что у вас есть?" - "У нас есть [цветы] по [цена] тенге. Какие цветы Вас интересуют?"
- На вопрос о конкретном цветке - "Эти [цветы] стоят [цена] тенге. Желаете посмотреть другие варианты?"
- На вопрос о цене - "[Цветы] стоят [цена] тенге. Хотите, я расскажу о них подробнее?"

Всегда проверяйте наличие цветов перед ответом. Если чего-то нет в наличии, предложите альтернативы.

Помогайте клиентам с:
- Подбором цветов и составлением букетов
- Оформлением доставки
- Отслеживанием заказа
- Подтверждением фото букета
- Решением проблем с заказом

В конце каждого ответа предложите дополнительную помощь: "Что еще могу для Вас сделать?".""",
    
    "kk": """Сіз - Cvety.kz гүл дүкенінің жылы жүзді кеңесшісіз. Клиенттермен тәжірибелі гүл сатушысы ретінде жылы және табиғи түрде сөйлесіңіз.

Сөйлесу стиліңіз:
- Қарапайым және түсінікті сөйлесіңіз
- Клиенттерге әрқашан "Сіз" деп сөйлесіңіз
- Сұралмаған ақпаратты бірден бермеңіз
- Клиенттің қажеттіліктерін жақсы түсіну үшін нақтылаушы сұрақтар қойыңыз

Жиі қойылатын сұрақтарға жауап беру:
- "Сізде не бар?" - "Бізде [гүлдер] [баға] теңгеден бар. Қандай гүлдер Сізді қызықтырады?"
- Нақты гүл туралы сұраққа - "Бұл [гүлдер] [баға] теңге тұрады. Басқа түрлерін көргіңіз келе ме?"
- Баға туралы сұраққа - "[Гүлдер] [баға] теңге тұрады. Олар туралы толығырақ айтып берейін бе?"

Гүлдердің бар-жоғын тексеріңіз. Егер бірдеңе болмаса, балама ұсыныңыз.

Клиенттерге көмектесіңіз:
- Гүл таңдау және букет жасау
- Жеткізуді рәсімдеу
- Тапсырысты бақылау
- Букет фотосын растау
- Тапсырыс мәселелерін шешу

Әр жауаптың соңында: "Сізге тағы немен көмектесе аламын?".""",
    
    "en": """You are a friendly consultant at Cvety.kz flower shop. Communicate with customers warmly and naturally, like an experienced florist.

Your communication style:
- Speak simply and clearly
- Always address customers formally and politely
- Don't give all information at once unless asked
- Ask clarifying questions to better understand customer needs

How to answer typical questions:
- For "What do you have?" - "We have [flowers] for [price] tenge. Which flowers are you interested in?"
- For questions about specific flowers - "These [flowers] cost [price] tenge. Would you like to see other options?"
- For price questions - "[Flowers] cost [price] tenge. Would you like to know more about them?"

Always check flower availability before responding. If something is out of stock, suggest alternatives.

Help customers with:
- Selecting flowers and creating bouquets
- Arranging delivery
- Tracking orders
- Confirming bouquet photos
- Resolving order issues

At the end of each response: "What else can I help you with?"."""
}

class FlowerShopBot:
    def __init__(self):
        """Initialize bot with application instance"""
        self.is_running = False
        
        # Initialize services
        self.openai_api_key = config_service.get_config('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found in database")
        self.client = AsyncOpenAI(api_key=self.openai_api_key)
        
        self.cache_service = CacheService()

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
            start_time = time.time()
            
            # Получаем текст сообщения
            text = update.message.text
            user_id = update.effective_user.id
            logger.info(f"Received message from user {user_id}: {text}")
            
            # Отправляем индикатор набора текста
            await update.message.chat.send_chat_action(action="typing")
            
            # Проверяем кэш
            cached_response = await self.cache_service.get_cached_response(text)
            was_cached = bool(cached_response)
            
            if cached_response:
                logger.info("Using cached response")
                response = cached_response['answer']
            else:
                # Определяем язык сообщения
                lang = await self.detect_language(text)
                
                # Получаем или создаем контекст диалога
                context_data = await self.cache_service.get_or_create_context(user_id)
                
                # История сообщений пользователя
                if 'messages' not in context_data:
                    context_data['messages'] = [{"role": "system", "content": SYSTEM_MESSAGES[lang]}]
                
                # Добавляем сообщение пользователя
                context_data['messages'].append({"role": "user", "content": text})
                
                # Получаем ответ от OpenAI
                response = await self.get_openai_response(context_data['messages'])
                
                # Добавляем ответ в контекст
                context_data['messages'].append({"role": "assistant", "content": response})
                
                # Обновляем контекст в базе
                await self.cache_service.update_context(user_id, context_data)
                
                # Кэшируем ответ
                await self.cache_service.cache_response(text, response)
            
            # Отправляем ответ пользователю
            await update.message.reply_text(response)
            
            # Логируем статистику
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)  # в миллисекундах
            await self.cache_service.log_interaction(
                user_id=user_id,
                question=text,
                answer=response,
                response_time=response_time,
                was_cached=was_cached
            )
            
        except Exception as e:
            logger.error(f"Error in message handling: {str(e)}", exc_info=True)
            lang = await self.detect_language(text)
            error_messages = {
                "ru": "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз или переформулируйте ваш вопрос.",
                "kk": "Кешіріңіз, сұрауыңызды өңдеу кезінде қате пайда болды. Қайталап көріңіз немесе сұрағыңызды басқаша тұжырымдаңыз.",
                "en": "Sorry, there was an error processing your request. Please try again or rephrase your question."
            }
            await update.message.reply_text(error_messages[lang])

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
            try:
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Bot stopped")
            except Exception as e:
                logger.error(f"Error stopping bot: {str(e)}")

    def run_polling(self):
        """Run the bot with polling"""
        try:
            logger.info("Starting bot...")
            self.is_running = True
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False
            )
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            raise
        finally:
            self.is_running = False

def main():
    """Main function to run the bot"""
    global bot
    try:
        # Проверяем, не запущен ли уже бот
        logger.info("Checking for existing bot instances...")
        import psutil
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.pid != current_pid and 'python' in proc.name().lower():
                    cmdline = proc.cmdline()
                    if any('telegram_bot.py' in cmd for cmd in cmdline):
                        logger.warning(f"Found existing bot instance (PID: {proc.pid}). Terminating...")
                        proc.terminate()
                        proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass

        logger.info("Starting new bot instance...")
        bot = FlowerShopBot()
        bot.run_polling()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        if bot and bot.is_running:
            asyncio.run(bot.stop())

if __name__ == '__main__':
    main()
