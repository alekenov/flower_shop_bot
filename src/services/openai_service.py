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
    
    async def get_response(self, user_message: str, inventory_info: str = None, user_id: int = None):
        """Получает ответ от OpenAI с учетом информации о товарах и базы знаний"""
        max_retries = 5
        base_retry_delay = 5  # начальная задержка в секундах
        
        # Получаем информацию из базы знаний
        try:
            knowledge_base = await self.docs_service.get_knowledge_base()
        except Exception as e:
            logger.error(f"Failed to get knowledge base: {e}")
            knowledge_base = ""
        
        for attempt in range(max_retries):
            try:
                system_prompt = """Ты - дружелюбный помощник цветочного магазина Cvety.kz в Казахстане. Твоя задача - помогать клиентам с выбором цветов, составлением букетов и отвечать на общие вопросы о магазине.
                
                ВАЖНЫЕ ПРАВИЛА:
                1. Всегда будь дружелюбным и позитивным 🌸
                2. Используй информацию из базы знаний для ответов на общие вопросы о магазине
                3. Для вопросов о цветах:
                   - Проверяй наличие и цены в актуальной информации о товарах
                   - Если спрашивают про цветы, которых нет - предложи альтернативы
                4. Если не знаешь точного ответа:
                   - НЕ отказывай сразу
                   - Предложи альтернативы или дополнительные опции
                   - Покажи готовность помочь с другими вопросами
                   - При необходимости, вежливо предложи связаться с менеджером
                5. Используй эмодзи для создания позитивного настроения 🌸
                6. ВАЖНО: Внимательно следи за контекстом разговора! Если клиент спрашивает о конкретном виде цветов,
                   продолжай разговор именно об этих цветах, не переходи на другие без явной необходимости.
                
                Примеры хороших ответов:
                
                На вопрос "Можно ли купить 100 роз?":
                "Конечно! 🌹 Мы можем организовать для вас большой заказ роз. Давайте я уточню детали:
                - Какой цвет роз вас интересует?
                - К какой дате нужны цветы?
                - Нужна ли особая упаковка?
                
                У нас сейчас есть красные розы по 410 тенге за штуку. Для больших заказов мы можем обсудить специальные условия. Хотите, я помогу рассчитать стоимость?"
                
                На вопрос про услугу, которой нет в базе:
                "Отличный вопрос! 🌸 Хотя у нас пока нет этой услуги, я могу предложить несколько альтернативных вариантов, которые могут вам подойти. Также я могу связать вас с нашим менеджером для обсуждения индивидуального решения. Что вас больше интересует?"
                
                ВАЖНО: 
                - Всегда предлагай альтернативы и дополнительные опции
                - Задавай уточняющие вопросы, чтобы лучше понять потребности клиента
                - Показывай готовность помочь и найти решение
                - Сохраняй контекст разговора и отвечай в соответствии с ним
                """

                messages = [
                    {"role": "system", "content": system_prompt}
                ]

                if knowledge_base:
                    messages.append({
                        "role": "system",
                        "content": f"База знаний магазина:\n{knowledge_base}"
                    })

                if inventory_info:
                    messages.append({
                        "role": "system",
                        "content": f"Актуальная информация о товарах:\n{inventory_info}"
                    })
                
                # Добавляем историю разговора для конкретного пользователя
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
                    max_tokens=500
                )
                
                bot_response = response.choices[0].message.content
                
                # Сохраняем сообщение пользователя и ответ бота в историю
                if user_id:
                    self.conversation_history[user_id].append({"role": "user", "content": user_message})
                    self.conversation_history[user_id].append({"role": "assistant", "content": bot_response})
                    
                    # Ограничиваем историю
                    if len(self.conversation_history[user_id]) > self.max_history * 2:  # *2 потому что каждый обмен это 2 сообщения
                        self.conversation_history[user_id] = self.conversation_history[user_id][-self.max_history * 2:]
                
                return bot_response

            except RateLimitError as e:
                logger.warning(f"Rate limit hit with model {current_model}, attempt {attempt + 1}/{max_retries}")
                if self.current_model_index < len(self.models) - 1:
                    self.current_model_index += 1
                    next_model = self.models[self.current_model_index]
                    logger.info(f"Switching to model: {next_model}")
                    continue  # Попробуем сразу с новой моделью
                else:
                    # Если все модели исчерпаны, ждем и возвращаемся к первой
                    self.current_model_index = 0
                    wait_time = base_retry_delay * (2 ** attempt)  # Экспоненциальная задержка
                    logger.info(f"All models exhausted. Waiting {wait_time} seconds before retry with {self.models[0]}")
                    await asyncio.sleep(wait_time)
                    continue

            except APIError as e:
                if "rate_limit" in str(e).lower():
                    # Обрабатываем так же, как RateLimitError
                    if self.current_model_index < len(self.models) - 1:
                        self.current_model_index += 1
                        next_model = self.models[self.current_model_index]
                        logger.info(f"Switching to model: {next_model}")
                        continue
                    else:
                        self.current_model_index = 0
                        wait_time = base_retry_delay * (2 ** attempt)
                        logger.info(f"All models exhausted. Waiting {wait_time} seconds before retry with {self.models[0]}")
                        await asyncio.sleep(wait_time)
                        continue
                logger.error(f"API error: {e}")
                wait_time = base_retry_delay * (attempt + 1)
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

        raise Exception("Failed to get response after maximum retries")
