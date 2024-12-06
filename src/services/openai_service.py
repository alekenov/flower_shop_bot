import logging
from openai import AsyncOpenAI
import os
import sys
import time
import asyncio
from openai import RateLimitError, APIError
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

    async def get_response(self, user_message: str, inventory_info: str = None):
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

                messages.append({
                    "role": "user",
                    "content": user_message
                })

                current_model = self.models[self.current_model_index]
                
                try:
                    response = await self.client.chat.completions.create(
                        model=current_model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500
                    )
                    return response.choices[0].message.content.strip()
                
                except RateLimitError as e:
                    logger.warning(f"Rate limit hit for model {current_model}, trying fallback...")
                    # Пробуем следующую модель
                    self.current_model_index = (self.current_model_index + 1) % len(self.models)
                    if attempt < max_retries - 1:
                        retry_delay = base_retry_delay * (2 ** attempt)  # Экспоненциальная задержка
                        logger.info(f"Retrying in {retry_delay} seconds with model {self.models[self.current_model_index]}")
                        await asyncio.sleep(retry_delay)
                        continue
                    raise

                except APIError as e:
                    if "rate_limit_exceeded" in str(e).lower():
                        # То же самое, что и для RateLimitError
                        self.current_model_index = (self.current_model_index + 1) % len(self.models)
                        if attempt < max_retries - 1:
                            retry_delay = base_retry_delay * (2 ** attempt)
                            logger.info(f"Retrying in {retry_delay} seconds with model {self.models[self.current_model_index]}")
                            await asyncio.sleep(retry_delay)
                            continue
                    raise
                
            except Exception as e:
                logger.error(f"Error getting OpenAI response: {e}")
                if attempt == max_retries - 1:
                    return ("Извините, сейчас наш сервис испытывает технические трудности. "
                           "Пожалуйста, напишите ваш вопрос менеджеру магазина, "
                           "и он поможет вам как можно скорее! 🌸")
                await asyncio.sleep(base_retry_delay * (2 ** attempt))
