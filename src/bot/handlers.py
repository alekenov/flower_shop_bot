import logging
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.services.sheets_service import SheetsService
from src.services.openai_service import OpenAIService
from src.services.docs_service import DocsService

logger = logging.getLogger(__name__)

# Инициализация сервисов
sheets_service = SheetsService()
openai_service = OpenAIService()
docs_service = DocsService()

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
        
        # Фразы, указывающие на то, что бот не уверен или дает общий ответ
        uncertain_phrases = [
            "извините",
            "не могу",
            "не знаю",
            "затрудняюсь",
            "обратитесь к менеджеру",
            "свяжитесь с менеджером",
            "напишите менеджеру",
            "хороший вопрос",
            "интересный вопрос",
            "отличный вопрос",
            "давайте уточним",
            "могу предложить альтернативу",
            "для уточнения деталей",
            "индивидуальное решение",
            "специальные условия"
        ]
        
        # Определяем тип ответа для записи в документ
        response_type = "Требует улучшения"
        if any(phrase in response.lower() for phrase in ["извините", "не могу", "не знаю"]):
            response_type = "Нет ответа"
        elif any(phrase in response.lower() for phrase in uncertain_phrases):
            response_type = "Неточный ответ"
        
        if any(phrase in response.lower() for phrase in uncertain_phrases):
            try:
                # Добавляем вопрос в Google Docs
                await docs_service.add_unanswered_question(
                    question=update.message.text,
                    user_id=update.effective_user.id,
                    bot_response=response,
                    response_type=response_type
                )
                logger.info(f"Added question to Google Docs: {update.message.text} (Type: {response_type})")
            except Exception as e:
                logger.error(f"Failed to add question to Google Docs: {e}")
        
        # Отправляем ответ пользователю
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        error_message = "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
        await update.message.reply_text(error_message)
