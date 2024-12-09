import logging
from telegram import Update
from telegram.ext import ContextTypes
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.services.sheets_service import SheetsService
from src.services.openai_service import OpenAIService
from src.services.docs_service import DocsService
from src.services.channel_logger import ChannelLogger

logger = logging.getLogger(__name__)

# Инициализация сервисов
sheets_service = SheetsService()
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
    else:
        await update.message.reply_text(
            "Чтобы узнать ID канала:\n"
            "1. Отправьте любое сообщение в ваш канал\n"
            "2. Перешлите это сообщение мне\n"
            "Я покажу вам ID канала"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        user_message = update.message.text.lower()
        logger.info(f"Получено сообщение: {user_message}")
        
        # Проверяем, спрашивает ли пользователь о цене или наличии конкретных цветов
        inventory_keywords = ['цена', 'стоит', 'стоят', 'наличие', 'есть', 'остались', 'купить']
        
        if any(keyword in user_message for keyword in inventory_keywords):
            logger.info("Обнаружен вопрос о ценах/наличии")
            try:
                # Получаем данные из Google Sheets
                inventory = await sheets_service.get_inventory_data()
                logger.info(f"Получены данные из таблицы: {inventory}")
                
                # Ищем упоминания конкретных цветов в сообщении
                mentioned_flowers = []
                for item in inventory:
                    name_parts = item['name'].lower().split()
                    category_parts = item['category'].lower().split()
                    
                    # Проверяем каждое слово из названия и категории
                    all_parts = name_parts + category_parts
                    if any(part in user_message for part in all_parts):
                        mentioned_flowers.append(item)
                
                if mentioned_flowers:
                    # Если спрашивают про конкретные цветы
                    response = ""
                    for flower in mentioned_flowers:
                        status = "в наличии" if flower['quantity'] > 0 else "нет в наличии"
                        response += f"🌸 {flower['name']}:\n"
                        response += f"   • Цена: {flower['price']}\n"
                        if flower['description']:
                            response += f"   • {flower['description']}\n"
                        response += f"   • Статус: {status}\n\n"
                elif "что" in user_message and "наличии" in user_message:
                    # Если спрашивают что есть в наличии
                    available_flowers = [item for item in inventory if item['quantity'] > 0]
                    if available_flowers:
                        response = "В нашем магазине сейчас в наличии:\n\n"
                        for flower in available_flowers:
                            response += f"🌸 {flower['name']}\n"
                            response += f"   • Цена: {flower['price']}\n"
                            if flower['description']:
                                response += f"   • {flower['description']}\n"
                            response += "\n"
                    else:
                        response = "К сожалению, сейчас все цветы распроданы. Новое поступление ожидается в ближайшее время."
                else:
                    # Если цветы не найдены в сообщении
                    response = await openai_service.get_response(
                        update.message.text,
                        user_id=update.effective_user.id
                    )
            except Exception as e:
                logger.error(f"Ошибка при получении данных из таблицы: {e}")
                response = await openai_service.get_response(
                    update.message.text,
                    user_id=update.effective_user.id
                )
        else:
            logger.info("Обычный вопрос, используем OpenAI")
            response = await openai_service.get_response(
                update.message.text,
                user_id=update.effective_user.id
            )
        
        # Отправляем ответ пользователю
        await update.message.reply_text(response)
        
        # Логируем взаимодействие
        await channel_logger.log_interaction(
            user_id=update.effective_user.id,
            username=update.effective_user.username,
            message=update.message.text,
            response=response
        )
        
    except Exception as e:
        error_message = "Извините, произошла ошибка. Попробуйте повторить запрос позже."
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text(error_message)

# Удаляем неправильно размещенные обработчики
