import logging
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os
import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.services.supabase_service import SupabaseService
from src.services.openai_service import OpenAIService
from src.services.docs_service import DocsService
from src.services.channel_logger import ChannelLogger

logger = logging.getLogger(__name__)

# Инициализация сервисов
supabase_service = SupabaseService()
openai_service = OpenAIService()
docs_service = DocsService()
channel_logger = ChannelLogger()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = (
        "👋 Добро пожаловать в наш цветочный магазин!\n\n"
        "Я помогу вам выбрать цветы и составить букет. "
        "Просто напишите, что вы хотите узнать, например:\n"
        "- Какие цветы есть в наличии?\n"
        "- Сколько стоят розы?\n"
        "- Хочу купить букет из пионов\n\n"
        "Чтобы получить помощь, используйте команду /help"
    )
    await update.message.reply_text(welcome_message)
    
    # Сохраняем информацию о новом пользователе
    user = update.effective_user
    await supabase_service.update_user_preferences(user.id, {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code
    })

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🌸 Я могу помочь вам:\n\n"
        "- Узнать наличие и цены на цветы\n"
        "- Подобрать букет\n"
        "- Ответить на вопросы о цветах\n\n"
        "Просто напишите свой вопрос, и я постараюсь помочь!"
    )
    await update.message.reply_text(help_text)

async def get_channel_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /channel_id"""
    if update.message.forward_from_chat:
        channel_id = update.message.forward_from_chat.id
        await update.message.reply_text(
            f"ID канала: {channel_id}\n\n"
            f"Добавьте этот ID в файл .env как:\n"
            f"TELEGRAM_LOG_CHANNEL_ID={channel_id}"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user_message = update.message.text
        user_id = update.effective_user.id
        
        # Получаем контекст разговора
        conversation_context = await supabase_service.get_conversation_context(user_id)
        
        # Получаем актуальные данные о продуктах
        products = await supabase_service.get_products()
        
        # Получаем предпочтения пользователя
        user_preferences = await supabase_service.get_user_preferences(user_id)
        
        # Формируем контекст для OpenAI
        context_data = {
            'products': products,
            'user_preferences': user_preferences,
            'conversation_context': conversation_context,
            'current_time': datetime.datetime.now().isoformat()
        }
        
        # Получаем ответ от OpenAI
        response = await openai_service.get_response(user_message, context_data)
        
        # Отправляем ответ пользователю
        await update.message.reply_text(response)
        
        # Сохраняем разговор
        await supabase_service.save_conversation(user_id, user_message, response)
        
        # Анализируем сообщение для сбора инсайтов
        await analyze_message(user_id, user_message, response)
        
        # Логируем в канал
        await channel_logger.log_message(update.message, response)
        
    except Exception as e:
        error_message = f"Произошла ошибка: {str(e)}"
        logger.error(error_message, exc_info=True)
        await update.message.reply_text(
            "Извините, произошла ошибка. Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

async def analyze_message(user_id: int, user_message: str, bot_response: str):
    """Анализ сообщения для сбора инсайтов"""
    try:
        # Анализируем намерения пользователя
        intent = await openai_service.analyze_intent(user_message)
        
        # Сохраняем инсайт
        await supabase_service.save_user_insight(user_id, 'message_intent', {
            'message': user_message,
            'intent': intent
        })
        
        # Сохраняем паттерн взаимодействия
        await supabase_service.save_interaction_pattern(user_id, 'conversation', {
            'user_message': user_message,
            'bot_response': bot_response,
            'intent': intent
        })
        
    except Exception as e:
        logger.error(f"Failed to analyze message: {str(e)}", exc_info=True)
