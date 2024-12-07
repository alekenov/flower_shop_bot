import logging
from telegram import Update
from telegram.ext import ContextTypes
from ..services.openai_service import OpenAIService
from ..services.sheets_service import GoogleSheetsService
from .keyboards import get_main_keyboard

logger = logging.getLogger(__name__)
openai_service = OpenAIService()
sheets_service = GoogleSheetsService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = (
        "👋 Здравствуйте! Я бот цветочного магазина.\n\n"
        "Я могу помочь вам с:\n"
        "🌸 Информацией о наличии цветов\n"
        "🚚 Условиями доставки\n"
        "💰 Ценами на букеты\n"
        "⏰ Графиком работы\n\n"
        "Чем могу помочь?"
    )
    await update.message.reply_text(welcome_message, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "Вот что я умею:\n\n"
        "/start - Начать общение\n"
        "/help - Показать это сообщение\n\n"
        "Также вы можете просто написать свой вопрос, и я постараюсь помочь!"
    )
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    try:
        # Логируем сообщение
        logger.info(f"Received message from {user_id}: {user_message}")
        
        # Получаем ответ от OpenAI
        response = await openai_service.get_response(user_message)
        
        # Сохраняем диалог в Google Sheets
        sheets_service.log_conversation(user_id, user_message, response)
        
        await update.message.reply_text(response, reply_markup=get_main_keyboard())
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего сообщения. "
            "Пожалуйста, попробуйте позже или свяжитесь с нашими менеджерами."
        )
