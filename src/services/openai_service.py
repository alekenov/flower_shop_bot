import logging
from openai import AsyncOpenAI
import os
import sys
import time
import asyncio
from openai import RateLimitError, APIError
from collections import defaultdict
import re
from typing import List, Dict
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config.config import Config
from src.services.docs_service import DocsService
from src.services.cache_service import CacheService
from src.services.emotion_analyzer import EmotionAnalyzer
from src.services.knowledge_base_service import KnowledgeBaseService
from src.services.dialogue_manager import DialogueManager
from .credentials_service import credentials_service
from src.prompts.system_prompts import get_prompt
from src.services.monitoring_service import MonitoringService, TokenUsage, ResponseQuality

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        # Получаем учетные данные из базы
        api_key = credentials_service.get_credential('openai', 'api_key')
        self.model = credentials_service.get_credential('openai', 'model')
        
        self.client = AsyncOpenAI(
            api_key=api_key
        )
        
        self.docs_service = DocsService()
        self.cache_service = CacheService()
        self.emotion_analyzer = EmotionAnalyzer()
        self.knowledge_base = KnowledgeBaseService()
        self.dialogue_manager = DialogueManager()
        self.monitoring = MonitoringService()
        
        # Параметры модели
        self.model_config = {
            "temperature": 0.7,  # Баланс между креативностью и точностью
            "max_tokens": 500,   # Максимальная длина ответа
            "presence_penalty": 0.1,  # Небольшой штраф за повторения
            "frequency_penalty": 0.1,  # Небольшой штраф за частые слова
        }
        
    async def get_relevant_knowledge(self, user_message: str) -> str:
        """Получает релевантную информацию из базы знаний на основе вопроса пользователя."""
        try:
            # Получаем релевантный контент с помощью нового сервиса
            relevant_sections = await self.knowledge_base.find_relevant_content(
                user_message,
                max_results=3
            )
            
            if not relevant_sections:
                return ""
                
            # Форматируем результаты
            formatted_content = []
            for content, score in relevant_sections:
                formatted_content.append(f"{content.strip()}\n")
                
            return "\n\n".join(formatted_content)
            
        except Exception as e:
            logger.error(f"Failed to get relevant knowledge: {e}")
            return ""

    async def get_response(self, user_message: str, inventory_info: str = None, user_id: int = None):
        """Получает ответ от OpenAI с учетом информации о товарах и базы знаний"""
        
        # Анализируем эмоции пользователя
        emotion_analysis = await self.emotion_analyzer.analyze(user_message)
        logger.info(f"Emotion analysis: {emotion_analysis}")
        
        # Проверяем кэш перед запросом к API
        cached_response = await self.cache_service.get_cached_response(user_message)
        if cached_response:
            logger.info("Using cached response")
            # Добавляем сообщение в историю даже при использовании кэша
            if user_id:
                await self.dialogue_manager.add_message(user_id, user_message, 'user')
                await self.dialogue_manager.add_message(user_id, cached_response, 'assistant')
            return cached_response
            
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

        start_time = time.time()
        for attempt in range(max_retries):
            try:
                system_prompt = self._get_system_prompt(user_message)
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
                
                # Добавляем информацию об эмоциях в системный промпт
                if emotion_analysis['dominant_emotions']:
                    messages.append({
                        "role": "system",
                        "content": f"Пользователь проявляет следующие эмоции: {', '.join(emotion_analysis['dominant_emotions'])}. "
                                 f"Рекомендации по общению: {', '.join(emotion_analysis['recommendations'])}"
                    })
                
                # Добавляем историю разговора
                if user_id:
                    # Получаем релевантный контекст
                    relevant_context = await self.dialogue_manager.get_relevant_context(
                        user_id,
                        user_message,
                        max_messages=5
                    )
                    messages.extend([
                        {'role': msg['role'], 'content': msg['content']}
                        for msg in relevant_context
                    ])
                    
                # Оптимизируем контекст диалога
                messages = self._optimize_context(messages)
                    
                # Добавляем текущее сообщение пользователя
                messages.append({
                    "role": "user",
                    "content": user_message
                })

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **self.model_config
                )
                
                bot_response = response.choices[0].message.content
                
                # Сохраняем ответ в кэш
                await self.cache_service.cache_response(user_message, bot_response)
                
                # Сохраняем сообщение пользователя и ответ бота в историю
                if user_id:
                    await self.dialogue_manager.add_message(user_id, user_message, 'user')
                    await self.dialogue_manager.add_message(user_id, bot_response, 'assistant')
                
                # Логируем использование токенов
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    cost_usd=self._calculate_cost(response.usage),
                    scenario=self._detect_scenario(user_message),
                    message_id=user_id  # Предполагается, что у вас есть user_id
                )
                await self.monitoring.log_token_usage(usage)
                
                # Оцениваем качество ответа
                quality = ResponseQuality(
                    message_id=user_id,
                    scenario=self._detect_scenario(user_message),
                    response_relevance=self._evaluate_relevance(user_message, response.choices[0].message.content),
                    format_compliance=self._check_format_compliance(response.choices[0].message.content),
                    emotional_match=self._check_emotional_match(user_message, response.choices[0].message.content),
                    flags=self._check_response_flags(response.choices[0].message.content),
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
                await self.monitoring.log_response_quality(quality)
                
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
                logger.warning(f"API error, retrying...")
                
            except Exception as e:
                logger.error(f"Error getting OpenAI response: {str(e)}")
                raise

    def _detect_scenario(self, user_message: str) -> str:
        """Определить сценарий на основе сообщения пользователя."""
        message = user_message.lower()
        
        # Проверяем наличие и цены
        if any(word in message for word in ['есть', 'наличие', 'цена', 'стоит', 'почем']):
            return 'availability'
            
        # Проверяем заказ
        if any(word in message for word in ['заказ', 'купить', 'оформить', 'доставка']):
            return 'order'
            
        # По умолчанию считаем FAQ
        return 'faq'

    def _detect_emotion(self, user_message: str) -> str:
        """Определить эмоциональный контекст сообщения."""
        message = user_message.lower()
        
        # Проверяем срочность
        if any(word in message for word in ['срочно', 'быстро', 'сейчас', 'скорее']):
            return 'urgent'
            
        # Проверяем позитив
        if any(word in message for word in ['спасибо', 'отлично', 'здорово', 'рад']):
            return 'positive'
            
        # Проверяем негатив
        if any(word in message for word in ['жаль', 'плохо', 'грустно', 'печаль']):
            return 'negative'
            
        return 'neutral'

    def _get_system_prompt(self, user_message: str) -> str:
        """Получить системный промпт на основе контекста."""
        scenario = self._detect_scenario(user_message)
        emotion = self._detect_emotion(user_message)
        return get_prompt(scenario, emotion)

    def _optimize_context(self, messages: List[Dict[str, str]], max_tokens: int = 2000) -> List[Dict[str, str]]:
        """Оптимизирует контекст диалога для уменьшения использования токенов.
        
        Примеры:
        1. Длинный диалог:
        Было:
        - User: Здравствуйте, хочу заказать букет роз
        - Assistant: Какие розы вы хотели бы? У нас есть...
        - User: Красные розы
        - Assistant: Сколько роз вы хотели бы?
        - User: 11 штук
        - Assistant: Хорошо. Адрес доставки?
        ...еще 10 сообщений...
        
        Стало:
        - System: Текущий заказ: красные розы, 11 штук
        - User: Адрес доставки?
        
        2. Сжатие длинных сообщений:
        Было:
        - User: У вас есть розы? А если есть, то какие цвета? 
               И еще хотел узнать про доставку, 
               сколько она стоит и как быстро привезут...
        
        Стало:
        - User: Вопросы: 1) наличие роз 2) цвета 3) условия доставки
        
        3. Удаление неважных сообщений:
        - Приветствия
        - Благодарности
        - Общие фразы
        """
        if not messages:
            return messages
            
        # 1. Ограничиваем количество сообщений
        if len(messages) > 10:
            # Оставляем только последние важные сообщения
            important_messages = []
            for msg in reversed(messages):
                # Пропускаем приветствия и благодарности
                if any(phrase in msg['content'].lower() for phrase in 
                      ['здравствуйте', 'привет', 'спасибо', 'пожалуйста']):
                    continue
                important_messages.append(msg)
                if len(important_messages) >= 5:  # Оставляем последние 5 важных сообщений
                    break
            messages = list(reversed(important_messages))
            
        # 2. Сжимаем длинные сообщения
        for msg in messages:
            if len(msg['content']) > 200:  # Если сообщение длиннее 200 символов
                # Извлекаем ключевые моменты
                content = msg['content']
                # Убираем лишние пробелы и переносы
                content = ' '.join(content.split())
                # Сокращаем длинные вопросы
                if 'есть ли у вас' in content.lower():
                    content = content.replace('есть ли у вас', 'наличие:')
                if 'сколько стоит' in content.lower():
                    content = content.replace('сколько стоит', 'цена:')
                # Обновляем сообщение
                msg['content'] = content
                
        # 3. Добавляем сводку контекста
        if len(messages) > 2:
            context = self._create_context_summary(messages)
            messages.insert(0, {
                'role': 'system',
                'content': f'Контекст диалога: {context}'
            })
            
        return messages
        
    def _create_context_summary(self, messages: List[Dict[str, str]]) -> str:
        """Создает краткую сводку контекста диалога.
        
        Пример:
        Диалог о заказе: красные розы (11 шт), 
        этап: уточнение адреса доставки
        """
        # Анализируем сообщения для выявления контекста
        context = []
        
        # Определяем тип диалога
        dialog_type = self._detect_dialog_type(messages)
        if dialog_type:
            context.append(f"Тип диалога: {dialog_type}")
            
        # Собираем детали заказа если это заказ
        if dialog_type == 'order':
            details = self._extract_order_details(messages)
            if details:
                context.append(f"Детали заказа: {details}")
                
        # Определяем текущий этап
        current_stage = self._detect_current_stage(messages)
        if current_stage:
            context.append(f"Текущий этап: {current_stage}")
            
        return '; '.join(context)

    def _detect_dialog_type(self, messages: List[Dict[str, str]]) -> str:
        """Определяет тип диалога: заказ, справка о наличии, общий вопрос и т.д."""
        # Анализируем последние сообщения
        for msg in reversed(messages):
            content = msg['content'].lower()
            if any(word in content for word in ['заказ', 'купить', 'доставка']):
                return 'order'
            if any(word in content for word in ['есть', 'наличие', 'цена']):
                return 'availability'
        return 'general'

    def _extract_order_details(self, messages: List[Dict[str, str]]) -> str:
        """Извлекает детали заказа из сообщений."""
        details = []
        for msg in messages:
            content = msg['content'].lower()
            # Ищем упоминания цветов и количества
            if 'роз' in content or 'тюльпан' in content or 'лили' in content:
                # Извлекаем количество если есть
                numbers = re.findall(r'\d+', content)
                if numbers:
                    details.append(f"{content.split()[0]} {numbers[0]} шт")
                else:
                    details.append(content.split()[0])
        return ', '.join(details) if details else None

    def _detect_current_stage(self, messages: List[Dict[str, str]]) -> str:
        """Определяет текущий этап диалога."""
        last_bot_msg = next((msg['content'].lower() for msg in reversed(messages) 
                           if msg['role'] == 'assistant'), '')
        
        if 'адрес' in last_bot_msg:
            return 'уточнение адреса'
        if 'телефон' in last_bot_msg or 'контакт' in last_bot_msg:
            return 'сбор контактов'
        if 'врем' in last_bot_msg or 'дат' in last_bot_msg:
            return 'уточнение времени'
        return None

    def _calculate_cost(self, usage) -> float:
        """Рассчитывает стоимость запроса."""
        # Цены могут меняться, берем из конфига или константы
        PROMPT_PRICE_PER_1K = 0.0015
        COMPLETION_PRICE_PER_1K = 0.002
        
        prompt_cost = (usage.prompt_tokens / 1000) * PROMPT_PRICE_PER_1K
        completion_cost = (usage.completion_tokens / 1000) * COMPLETION_PRICE_PER_1K
        return prompt_cost + completion_cost
        
    def _evaluate_relevance(self, query: str, response: str) -> float:
        """Оценивает релевантность ответа запросу."""
        # Простая эвристика: проверяем наличие ключевых слов
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        common_words = query_words.intersection(response_words)
        return len(common_words) / len(query_words) if query_words else 0.0
        
    def _check_format_compliance(self, response: str) -> float:
        """Проверяет соответствие формату ответа."""
        # Пример проверки формата для цен
        if 'тг' in response.lower():
            # Проверяем формат цены: число + "тг"
            price_format = re.compile(r'\d+\s*тг')
            matches = price_format.findall(response.lower())
            return 1.0 if matches else 0.0
        return 1.0  # Если цена не упоминается, считаем формат правильным
        
    def _check_emotional_match(self, query: str, response: str) -> float:
        """Проверяет соответствие эмоционального тона."""
        emotion = self._detect_emotion(query)
        
        # Проверяем соответствие тона
        if emotion == 'positive':
            positive_words = ['рад', 'отлично', 'прекрасно', 'с удовольствием']
            score = sum(1 for word in positive_words if word in response.lower())
            return min(score / 2, 1.0)
        elif emotion == 'negative':
            polite_words = ['извините', 'сожалеем', 'понимаем', 'поможем']
            score = sum(1 for word in polite_words if word in response.lower())
            return min(score / 2, 1.0)
        return 1.0  # Для нейтрального тона
        
    def _check_response_flags(self, response: str) -> Dict[str, bool]:
        """Проверяет наличие проблем в ответе."""
        return {
            'missing_price': 'тг' not in response.lower() and any(word in response.lower() for word in ['цена', 'стоит', 'рубл']),
            'incorrect_format': not re.search(r'\d+\s*тг', response.lower()) and 'тг' in response.lower(),
            'inappropriate_tone': False  # Требует более сложной логики
        }
