import asyncio
import logging
from services.docs_service import DocsService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        docs_service = DocsService()
        
        # Тест 1: Добавляем новый вопрос в FAQ
        await docs_service.add_faq_item(
            "Как заказать букет на определенное время?",
            "Вы можете указать желаемое время доставки при оформлении заказа. "
            "Мы принимаем заказы на конкретное время с запасом минимум 3 часа."
        )
        
        # Тест 2: Обновляем раздел с акциями
        await docs_service.update_section(
            "### 5.1 Текущие акции",
            """- Скидка 15% на все букеты из роз при заказе от 15 штук
- Бесплатная доставка при заказе от 20000 тенге
- Специальное предложение: букет недели со скидкой 20%"""
        )
        
        # Тест 3: Обновляем метаданные
        await docs_service.update_metadata()
        
        logger.info("All tests completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
