import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование с большей детализацией
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# Базовые ответы на частые вопросы
FAQ = {
    'время работы': 'Мы работаем ежедневно с 9:00 до 21:00',
    'доставка': 'Доставка осуществляется по городу в течение 2-3 часов. Стоимость доставки от 1000 тенге',
    'оплата': 'Принимаем наличные, банковские карты и kaspi переводы',
    'цены': 'Букеты от 5000 тенге. Для уточнения цен на конкретные букеты, пожалуйста, уточните какие цветы вас интересуют'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        'Добро пожаловать в бот цветочного магазина! 👋\n'
        'Я могу ответить на ваши вопросы о:\n'
        '- времени работы\n'
        '- доставке\n'
        '- способах оплаты\n'
        '- ценах на букеты\n\n'
        'Просто напишите ваш вопрос!'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих сообщений"""
    message = update.message.text.lower()
    
    # Поиск ответа в FAQ
    for key, response in FAQ.items():
        if key in message:
            await update.message.reply_text(response)
            return
    
    # Если ответ не найден
    await update.message.reply_text(
        'Извините, я не могу ответить на этот вопрос. '
        'Пожалуйста, свяжитесь с нашим менеджером по номеру +7-XXX-XXX-XXXX'
    )
    # Здесь можно добавить логирование необработанных вопросов

def main():
    """Запуск бота"""
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error('Не найден TELEGRAM_BOT_TOKEN в .env файле')
        return
    
    logger.info(f'Запуск бота с токеном: {token[:10]}...')
    
    try:
        # Создаем приложение
        application = Application.builder().token(token).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info('Бот успешно настроен и запускается...')
        
        # Запускаем бота
        application.run_polling()
    except Exception as e:
        logger.error(f'Ошибка при запуске бота: {e}')

if __name__ == '__main__':
    main() 