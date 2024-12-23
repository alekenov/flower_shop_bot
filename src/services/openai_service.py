import logging
import os
import time
from typing import Dict, List, Optional, Set
from openai import AsyncOpenAI
from services.config_service import config_service
from services.docs_service import DocsService
from services.sheets_service import SheetsService

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        # Получаем учетные данные из базы
        self.api_key = config_service.get_config('api_key', service_name='openai')
        self.model = config_service.get_config('model', service_name='openai') or "gpt-4-turbo-preview"
        
        self.client = AsyncOpenAI(
            api_key=self.api_key
        )
        
        self.docs_service = DocsService()
        self.sheets_service = SheetsService()
        
        # Параметры модели
        self.model_config = {
            "temperature": 0.7,
            "max_tokens": 500,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1,
        }
        
        # Базовые типы цветов для поиска
        self.flower_types = ['розы', 'тюльпаны', 'лилии', 'хризантемы', 'пионы']
        
        # Темы вопросов
        self.topics = {
            'доставка': ['доставк', 'привез', 'курьер', 'самовывоз'],
            'оплата': ['оплат', 'карт', 'наличн', 'каспи', 'kaspi', 'перевод'],
            'адрес': ['где', 'адрес', 'находит', 'распол', 'как добраться'],
            'время': ['время', 'график', 'работает', 'открыт', 'закрыт', 'часы'],
            'акции': ['акци', 'скидк', 'спецпредложен', 'бонус'],
            'контакты': ['контакт', 'связ', 'телефон', 'номер', 'уатсап', 'ватсап', 'whatsapp', 'вацап', 'what', 'app', 'вотсап']
        }

    def _get_requested_flowers(self, message: str) -> List[str]:
        """Определяет, спрашивают ли о конкретных цветах."""
        message = message.lower()
        flowers = []
        
        # Проверяем общие вопросы о наличии
        if any(word in message for word in ['что есть', 'какие цветы', 'что имеется', 'наличии', 'есть', 'имеются']):
            return ['все']
            
        # Ищем конкретные цветы
        if 'роз' in message:
            flowers.append('роз')
        if 'тюльпан' in message:
            flowers.append('тюльпан')
        if 'орхиде' in message:
            flowers.append('орхиде')
            
        return flowers

    def _get_topic(self, query: str) -> Optional[str]:
        """Определяет тему вопроса"""
        query = query.lower()
        logger.info(f"Определяем тему для вопроса: {query}")
        
        for topic, keywords in self.topics.items():
            found_keywords = [word for word in keywords if word in query]
            if found_keywords:
                logger.info(f"Найдена тема '{topic}' по ключевым словам: {found_keywords}")
                return topic
                
        logger.info("Тема не определена")
        return None

    def _validate_response(self, response: str, query: str) -> Optional[str]:
        """Проверяет полноту ответа."""
        query = query.lower()
        response = response.strip()
        
        # Проверка ответа про адрес
        if any(word in query for word in ['адрес', 'где', 'находитесь', 'расположен']):
            required = ['астана', 'достык', '5', 'офис', '46', 'керуен']
            missing = [word for word in required if word not in response.lower()]
            if missing:
                logger.warning(f"Неполный ответ про адрес. Отсутствуют: {missing}")
                return None
        
        # Проверка ответа про цветы
        if any(word in query for word in ['что есть', 'наличии', 'цены']):
            if not any(char.isdigit() for char in response):
                logger.warning("Ответ про цветы не содержит цен")
                return None
            if not any(word in response.lower() for word in ['тг', 'тенге']):
                logger.warning("Ответ про цветы не содержит валюту")
                return None
        
        # Проверка ответа про контакты
        if any(word in query for word in ['уатсап', 'ватсап', 'whatsapp', 'вацап', 'what', 'app', 'вотсап']):
            if not any(char.isdigit() for char in response):
                logger.warning("Ответ про WhatsApp не содержит номер")
                return None
            if '+7' not in response:
                logger.warning("Ответ про WhatsApp не содержит код страны")
                return None
        
        return response

    async def get_response(self, user_message: str, inventory_info: str = None, user_id: int = None):
        """Получает ответ от OpenAI с учетом информации о товарах и базы знаний"""
        max_retries = 3
        retry_count = 0
        
        try:
            # Определяем запрашиваемые цветы
            requested_flowers = self._get_requested_flowers(user_message)
            if requested_flowers:
                logger.info(f"Запрошены цветы: {requested_flowers}")
                # Получаем информацию о цветах
                flower_info = self.sheets_service.get_specific_flowers(requested_flowers)
                if flower_info:
                    logger.info(f"Найдена информация о цветах: {flower_info}")
                    return flower_info
                else:
                    logger.warning("Информация о запрошенных цветах не найдена")
                    return "Нет информации о запрошенных цветах"

            # Определяем тему вопроса
            topic = self._get_topic(user_message)
            if topic:
                logger.info(f"Определена тема: {topic}")
                # Получаем информацию из базы знаний
                kb_info = self.docs_service.find_relevant_section(user_message)
                if kb_info:
                    logger.info("Найдена релевантная информация в базе знаний")
                    context = [kb_info]
                else:
                    logger.warning("Не найдена релевантная информация в базе знаний")
                    context = []
            else:
                logger.info("Тема не определена")
                context = []

            logger.info(f"Итоговый контекст для OpenAI: {context}")

            while retry_count < max_retries:
                try:
                    # Формируем системный промпт
                    system_prompt = (
                        "Ты - помощник цветочного магазина. Правила ответов:\n"
                        "1. Предоставляй ПОЛНУЮ информацию из контекста\n"
                        "2. Не сокращай и не обрезай важные детали\n"
                        "3. Форматируй ответы по типам:\n"
                        "   - АДРЕС: [город], [улица], [номер офиса], [ориентиры]\n"
                        "   - ЦЕНЫ: каждый цветок с новой строки [название] - [цена]\n"
                        "   - КОНТАКТЫ: каждый контакт с новой строки\n"
                        "4. Примеры правильных ответов:\n"
                        "   ❌ Неправильно: 'Достык 5'\n"
                        "   ✅ Правильно: 'г. Астана, Достык 5, офис 46, вход со стороны Керуена'\n"
                        "   ❌ Неправильно: 'розы 1500'\n"
                        "   ✅ Правильно: 'Розы красные - 1500 тг\n"
                        "                 Розы белые - 1200 тг'\n"
                        "5. Не используй вежливые фразы\n"
                        "6. Не предлагай задавать дополнительные вопросы\n"
                        "7. НИКОГДА не добавляй информацию от себя\n"
                        "8. Если информации нет в контексте, отвечай 'Нет информации'"
                    )

                    # Формируем сообщения для модели
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": (
                            f"Контекст:\n{chr(10).join(context) if context else 'Нет информации'}\n\n"
                            f"Вопрос клиента: {user_message}"
                        )}
                    ]

                    # Получаем ответ от OpenAI
                    response = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=500,
                        presence_penalty=0.1,
                        frequency_penalty=0.1
                    )

                    # Получаем ответ
                    if response.choices and response.choices[0].message.content:
                        response = response.choices[0].message.content.strip()
                        
                        # Валидируем ответ
                        validated_response = self._validate_response(response, user_message)
                        if validated_response is None:
                            # Если ответ неполный, пробуем еще раз с уточнением
                            system_prompt += "\nВАЖНО: В предыдущем ответе не хватало важной информации. Убедись, что ответ содержит ВСЕ детали!"
                            messages = [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": (
                                    f"Контекст:\n{chr(10).join(context) if context else 'Нет информации'}\n\n"
                                    f"Вопрос клиента: {user_message}"
                                )}
                            ]
                            response = await self.client.chat.completions.create(
                                model=self.model,
                                messages=messages,
                                temperature=0.7,
                                max_tokens=500,
                                presence_penalty=0.1,
                                frequency_penalty=0.1
                            )
                            response = response.choices[0].message.content.strip()
                            validated_response = self._validate_response(response, user_message)
                            
                        return validated_response if validated_response else "Нет информации"
                    else:
                        logger.error("Empty response from OpenAI")
                        return "Нет информации"

                except Exception as e:
                    logger.error(f"Error on attempt {retry_count + 1}: {e}")
                    retry_count += 1
                    if retry_count == max_retries:
                        return "Произошла ошибка при получении ответа"
                    await asyncio.sleep(1)  # Пауза перед повторной попыткой

        except Exception as e:
            logger.error(f"Error getting OpenAI response: {e}")
            return "Произошла ошибка при получении ответа"
