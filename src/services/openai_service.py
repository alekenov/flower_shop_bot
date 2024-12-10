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
        
        # Получаем релевантную информацию из базы знаний только для вопросов не о наличии/ценах
        message_lower = user_message.lower()
        if not any(word in message_lower for word in ['цена', 'стоит', 'сколько', 'рубл', 'тенге', 'есть', 'наличие', 'купить']):
            try:
                relevant_knowledge = await self.get_relevant_knowledge(user_message)
                logger.info(f"Got relevant knowledge: {relevant_knowledge}")
            except Exception as e:
                logger.error(f"Failed to get relevant knowledge: {e}")
                relevant_knowledge = ""
        else:
            relevant_knowledge = ""
            logger.info("Skipping knowledge base for inventory-related question")
        
        for attempt in range(max_retries):
            try:
                system_prompt = self._get_system_prompt()
                messages = [
                    {"role": "system", "content": system_prompt}
                ]

                # Сначала добавляем информацию о товарах
                if inventory_info:
                    messages.append({
                        "role": "system",
                        "content": f"Актуальная информация о товарах:\n{inventory_info}"
                    })
                
                # Затем добавляем информацию из базы знаний (если есть)
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
                
                # Проверяем, нужно ли добавить вопрос в FAQ
                if "не знаю" in bot_response.lower() or "уточнить у менеджера" in bot_response.lower():
                    try:
                        await self.docs_service.add_unanswered_question(
                            user_message,
                            user_id,
                            bot_response,
                            "Требует дополнения базы знаний"
                        )
                    except Exception as e:
                        logger.error(f"Failed to add unanswered question: {e}")
                
                return bot_response

            except RateLimitError as e:
                logger.warning(f"Rate limit hit with model {current_model}, attempt {attempt + 1}/{max_retries}")
                if self.current_model_index < len(self.models) - 1:
                    self.current_model_index += 1
                    next_model = self.models[self.current_model_index]
                    logger.info(f"Switching to model: {next_model}")
                    continue
                else:
                    self.current_model_index = 0
                    wait_time = base_retry_delay * (2 ** attempt)
                    logger.info(f"All models exhausted. Waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                    continue

            except APIError as e:
                if "rate_limit" in str(e).lower():
                    if self.current_model_index < len(self.models) - 1:
                        self.current_model_index += 1
                        continue
                    else:
                        self.current_model_index = 0
                        wait_time = base_retry_delay * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        continue
                raise

        raise Exception("Failed to get response after maximum retries")

    def _get_system_prompt(self):
        """Get the system prompt for OpenAI."""
        return """Ты - дружелюбный и профессиональный консультант цветочного магазина. 

Основные правила:
1. ВСЕГДА используй ТОЛЬКО данные из inventory_info для информации о наличии и ценах цветов
2. НИКОГДА не используй данные о ценах и наличии из других источников
3. НИКОГДА не упоминай и не предлагай использовать команду /products
4. ВСЕГДА проверяй наличие цветов в inventory_info перед ответом
5. Отвечай ТОЛЬКО точными ценами и количеством из inventory_info
6. Если цветка нет в inventory_info - отвечай "К сожалению, этих цветов сейчас нет в наличии"
7. Не придумывай цены и наличие цветов

Примеры ответов:

Вопрос: "Сколько стоят розы?"
Ответ: "У нас есть красные розы по 1000 тенге за штуку, в наличии 50 штук"

Вопрос: "Есть ли тюльпаны?"
Ответ: "К сожалению, тюльпанов сейчас нет в наличии"

Вопрос: "Какие цветы есть?"
Ответ: "У нас в наличии:
- Красные розы: 1000 тенге, 50 штук
- Белые розы: 1200 тенге, 30 штук"
"""
