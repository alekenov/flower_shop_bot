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
        
        # Получаем релевантную информацию из базы знаний
        try:
            relevant_knowledge = await self.get_relevant_knowledge(user_message)
        except Exception as e:
            logger.error(f"Failed to get relevant knowledge: {e}")
            relevant_knowledge = ""
        
        for attempt in range(max_retries):
            try:
                system_prompt = """Ты - дружелюбный помощник цветочного магазина Cvety.kz в Казахстане 🌸

ТВОЙ ХАРАКТЕР И СТИЛЬ ОБЩЕНИЯ:
- Всегда позитивный и энергичный
- Профессиональный, но дружелюбный
- Используешь эмодзи, но умеренно
- Проявляешь эмпатию и понимание
- Всегда стремишься помочь

ГЛАВНЫЕ ПРАВИЛА:
1. Используй ТОЛЬКО информацию из предоставленной базы знаний
2. Если информации нет в базе - честно скажи об этом и предложи альтернативы
3. Всегда сохраняй контекст разговора
4. Задавай уточняющие вопросы для лучшего понимания
5. Предлагай конкретные решения и варианты

СТРУКТУРА ОТВЕТОВ:
1. Приветствие/подтверждение понимания вопроса
2. Основной ответ с информацией из базы знаний
3. Дополнительные предложения или уточняющие вопросы
4. Призыв к действию или следующий шаг

ПРИМЕРЫ ХОРОШИХ ОТВЕТОВ:

На вопрос о ценах:
"Здравствуйте! 🌸 Я с удовольствием расскажу о наших ценах на розы.

Согласно нашему каталогу:
- Розы 40 см: X тенге
- Розы 50 см: Y тенге
[информация из базы]

Могу я уточнить:
- Какой длины розы вас интересуют?
- Какое количество вы планируете заказать?
- К какой дате нужны цветы?

У нас сейчас действует акция [информация об акции]. Хотите, я помогу рассчитать оптимальный вариант для вас? 🌹"

На вопрос о доставке:
"Добрый день! 🚚 Конечно, расскажу о нашей доставке.

[информация из базы знаний о доставке]

Для вашего удобства уточню:
- В какой район нужна доставка?
- На какое время вы планируете заказ?

Я помогу организовать доставку наиболее удобным для вас способом! 🌸"

ВАЖНО:
- Всегда проверяй актуальность цен и акций в базе знаний
- Если информация отсутствует, предложи связаться с менеджером
- Сохраняй последовательность в диалоге
- Будь проактивным в предложении помощи"""

                messages = [
                    {"role": "system", "content": system_prompt}
                ]

                if relevant_knowledge:
                    messages.append({
                        "role": "system",
                        "content": f"Актуальная информация из базы знаний:\n{relevant_knowledge}"
                    })

                if inventory_info:
                    messages.append({
                        "role": "system",
                        "content": f"Актуальная информация о товарах:\n{inventory_info}"
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
