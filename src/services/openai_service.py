import logging
from openai import AsyncOpenAI
import os
import sys
import time
import asyncio
from openai import RateLimitError, APIError
from collections import defaultdict
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config.config import Config
from src.services.docs_service import DocsService

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        config = Config()
        self.client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY
        )
        self.docs_service = DocsService()
        # Список моделей в порядке предпочтения
        self.models = [
            "gpt-4-turbo-preview",  # Самая новая и мощная
            "gpt-4",                # Стабильная, но дороже
            "gpt-3.5-turbo-16k",    # Большой контекст
            "gpt-3.5-turbo",        # Базовая модель
        ]
        self.current_model_index = 3  # Начинаем с gpt-3.5-turbo
        
        # Хранение контекста для каждого пользователя
        self.conversation_history = defaultdict(list)
        # Максимальное количество сообщений в истории
        self.max_history = 10
    
    async def get_relevant_knowledge(self, user_message: str) -> str:
        """Получает релевантную информацию из базы знаний на основе вопроса пользователя."""
        try:
            # Определяем ключевые разделы для поиска на основе вопроса
            sections = []
            
            # Проверяем ключевые слова в вопросе
            message_lower = user_message.lower()
            
            if any(word in message_lower for word in ['цена', 'стоит', 'сколько', 'рубл', 'тенге']):
                sections.append("## 2. Каталог и цены")
            
            if any(word in message_lower for word in ['доставка', 'привезти', 'доставить', 'курьер']):
                sections.append("## 3. Доставка")
            
            if any(word in message_lower for word in ['оплата', 'оплатить', 'карта', 'наличные', 'kaspi']):
                sections.append("## 4. Оплата")
            
            if any(word in message_lower for word in ['акция', 'скидка', 'распродажа', 'спецпредложение']):
                sections.append("## 5. Специальные предложения")
            
            if any(word in message_lower for word in ['роза', 'розы']):
                sections.append("### 2.1 Розы")
            
            if any(word in message_lower for word in ['букет']):
                sections.append("### 2.2 Букеты")
            
            # Всегда проверяем FAQ
            sections.append("## 6. FAQ")
            
            # Собираем информацию из всех релевантных разделов
            relevant_info = []
            for section in sections:
                content = await self.docs_service.get_section_content(section)
                if content:
                    relevant_info.append(f"=== {section} ===\n{content}")
            
            return "\n\n".join(relevant_info)
            
        except Exception as e:
            logger.error(f"Failed to get relevant knowledge: {e}")
            return ""

    async def get_response(self, user_message: str, inventory_info: str = None, user_id: int = None):
        """Получает ответ от OpenAI с учетом информации о товарах и базы знаний"""
        max_retries = 5
        base_retry_delay = 5  # начальная задержка в секундах
        
        logger.info(f"Processing message from user {user_id}: {user_message}")
        logger.info(f"Inventory info: {inventory_info}")
        
        # Получаем релевантную информацию из базы знаний
        try:
            relevant_knowledge = await self.get_relevant_knowledge(user_message)
            logger.info(f"Got relevant knowledge: {relevant_knowledge}")
        except Exception as e:
            logger.error(f"Failed to get relevant knowledge: {e}")
            relevant_knowledge = ""

        for attempt in range(max_retries):
            try:
                system_prompt = self._get_system_prompt()
                messages = [
                    {"role": "system", "content": system_prompt}
                ]

                # Добавляем информацию о товарах
                if inventory_info:
                    messages.append({
                        "role": "system",
                        "content": f"Актуальный каталог цветов:\n{inventory_info}\n\nИспользуй ТОЛЬКО эти данные при ответе на вопросы о наличии и ценах."
                    })
                
                # Добавляем информацию из базы знаний
                if relevant_knowledge:
                    messages.append({
                        "role": "system",
                        "content": f"Дополнительная информация:\n{relevant_knowledge}"
                    })
                
                # Добавляем историю разговора
                if user_id:
                    messages.extend(self.conversation_history[user_id])
                
                # Добавляем текущее сообщение пользователя
                messages.append({
                    "role": "user",
                    "content": user_message
                })

                current_model = self.models[self.current_model_index]
                
                response = await self.client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=800
                )
                
                bot_response = response.choices[0].message.content
                
                # Сохраняем сообщение пользователя и ответ бота в историю
                if user_id:
                    self.conversation_history[user_id].append({"role": "user", "content": user_message})
                    self.conversation_history[user_id].append({"role": "assistant", "content": bot_response})
                    
                    # Ограничиваем историю
                    if len(self.conversation_history[user_id]) > self.max_history * 2:
                        self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history * 2:]
                
                return bot_response

            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise
                # Увеличиваем задержку с каждой попыткой
                delay = base_retry_delay * (2 ** attempt)
                logger.warning(f"Rate limit hit, waiting {delay} seconds...")
                await asyncio.sleep(delay)
                
            except APIError as e:
                if attempt == max_retries - 1:
                    raise
                # Пробуем использовать следующую модель
                self.current_model_index = min(self.current_model_index + 1, len(self.models) - 1)
                logger.warning(f"API error, switching to model {self.models[self.current_model_index]}")
                
            except Exception as e:
                logger.error(f"Error getting OpenAI response: {str(e)}")
                raise

    def _get_system_prompt(self):
        """Get the system prompt for OpenAI."""
        return """Ты - помощник цветочного магазина Flower Shop Bot. Твоя задача - помогать клиентам с выбором цветов, предоставлять информацию о товарах и помогать с оформлением заказов.

Правила общения:
1. Всегда будь вежливым и дружелюбным
2. Отвечай кратко и по существу
3. Используй ТОЛЬКО актуальные данные из таблицы инвентаря
4. Если товара нет в наличии - предложи альтернативы из имеющихся
5. Используй эмодзи для украшения ответов 🌸
6. Всегда указывай цену в тенге (тг)
7. Форматируй ответ, чтобы он был легко читаемым

Доступные функции:
1. list_available_products() - получить список всех доступных товаров
2. get_product_info(product_name) - получить информацию о конкретном товаре
3. check_availability(product_name, quantity) - проверить наличие товара в нужном количестве
4. place_order(...) - оформить заказ

Алгоритм работы с заказами:
1. При запросе о наличии:
   - Используй get_product_info() для получения информации
   - Если товар есть, укажи цену и доступное количество
   - Если товара нет, используй list_available_products() и предложи альтернативы

2. При оформлении заказа:
   - Проверь наличие через check_availability()
   - Если товара достаточно, собери все необходимые данные:
     * Название товара
     * Количество
     * Адрес доставки
     * Дату доставки
     * Имя получателя
     * Телефон
   - Используй place_order() для создания заказа
   - Сообщи клиенту номер заказа и сумму к оплате

3. При вопросах о ценах:
   - Используй get_product_info()
   - Укажи цену за штуку
   - При заказе от 10 штук предложи связаться с менеджером для обсуждения скидки

Примеры ответов:

На вопрос о наличии:
🌸 В наличии:
- Красные розы: 5000 тг/шт (50 шт)
- Белые лилии: 3000 тг/шт (осталось мало - 5 шт)
- Тюльпаны: 2000 тг/шт (100 шт)

При оформлении заказа:
✨ Заказ №ORD-123 успешно создан!
Детали заказа:
- Товар: Красные розы (5 шт)
- Сумма: 25000 тг
- Доставка: 1500 тг
Итого к оплате: 26500 тг
"""
