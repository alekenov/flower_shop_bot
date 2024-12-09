import asyncio
import logging
from services.openai_service import OpenAIService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_responses():
    openai_service = OpenAIService()
    
    # Тестовые вопросы
    test_questions = [
        "Сколько стоят розы?",
        "Как можно оплатить заказ?",
        "Есть ли сейчас какие-нибудь акции?",
        "Можете ли вы доставить букет завтра утром?",
        "Хочу заказать букет на свадьбу, что посоветуете?"
    ]
    
    # Тестируем каждый вопрос
    for question in test_questions:
        logger.info(f"\nТестируем вопрос: {question}")
        try:
            response = await openai_service.get_response(question, user_id=123)
            logger.info(f"Ответ бота:\n{response}\n")
            logger.info("-" * 50)
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса '{question}': {e}")

if __name__ == "__main__":
    asyncio.run(test_responses())
