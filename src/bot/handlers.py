import logging
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.services.sheets_service import SheetsService
from src.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

# Инициализация сервисов
sheets_service = SheetsService()
openai_service = OpenAIService()

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        # Получаем информацию о товарах
        inventory = await sheets_service.get_inventory_data()
        inventory_info = sheets_service.format_inventory_for_openai(inventory)
        
        # Получаем ответ от OpenAI
        response = await openai_service.get_response(update.message.text, inventory_info)
        
        # Отправляем ответ пользователю
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        error_message = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
        await update.message.reply_text(error_message)
