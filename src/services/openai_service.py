import logging
from openai import AsyncOpenAI
import os
import sys
import time
import asyncio
from openai import RateLimitError
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config.config import Config

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        config = Config()
        self.client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY
        )

    async def get_response(self, user_message: str, inventory_info: str = None):
        """Получает ответ от OpenAI с учетом информации о товарах"""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                system_prompt = """Ты - помощник цветочного магазина в Казахстане. Твоя задача - помогать клиентам с выбором цветов и составлением букетов.
                
                ВАЖНЫЕ ПРАВИЛА:
                1. НИКОГДА не упоминай цветы, которых нет в актуальной информации о товарах
                2. Если спрашивают "какие цветы есть?", перечисляй ТОЛЬКО те, что указаны в актуальной информации
                3. Всегда проверяй наличие и цену цветов ТОЛЬКО из актуальной информации о товарах
                4. Если клиент спрашивает о цветах, которых нет в наличии, вежливо сообщи что их нет и предложи те, что есть в наличии
                5. НИКОГДА не упоминай цены в рублях или других валютах - используй ТОЛЬКО тенге
                6. НИКОГДА не делай конвертацию валют - все цены должны быть указаны строго в тенге как в актуальной информации
                7. Учитывай количество товара в наличии
                8. Отвечай кратко и по делу
                9. Используй эмодзи для украшения ответов 🌸
                
                На вопрос "какие цветы есть в наличии?" отвечай СТРОГО по формату:
                "В наличии есть: [перечисли только те цветы, что есть в актуальной информации, с количеством и ценой в тенге]"
                
                Примеры ответов:
                - О наличии: "В наличии есть: красные розы (20 шт.) по 410 тенге и пионы (30 шт.) по 1800 тенге 🌸"
                - На вопрос о цене: "Красные розы стоят 410 тенге за штуку 🌹"
                - Если товара нет: "К сожалению, [название цветка] сейчас нет в наличии. Но у нас есть [перечисли имеющиеся]"
                """

                if inventory_info:
                    system_prompt += f"\n\nАктуальная информация о товарах (ОТВЕЧАЙ ТОЛЬКО ПРО ЭТИ ЦВЕТЫ):\n{inventory_info}"

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ]

                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500
                )

                return response.choices[0].message.content

            except RateLimitError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Rate limit exceeded, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Увеличиваем задержку с каждой попыткой
                else:
                    logger.error(f"Rate limit exceeded after {max_retries} attempts")
                    return "Извините, сервис временно перегружен. Пожалуйста, попробуйте через несколько минут."

            except Exception as e:
                logger.error(f"Error getting OpenAI response: {e}")
                return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."
