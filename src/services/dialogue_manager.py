import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
from collections import defaultdict

logger = logging.getLogger(__name__)

class DialogueManager:
    def __init__(self):
        # Хранение истории диалогов по пользователям
        self.conversations = defaultdict(list)
        
        # Максимальное количество сообщений в истории
        self.max_history_size = 10
        
        # Время жизни сообщений (в часах)
        self.message_ttl = 24
        
        # Веса для разных типов сообщений
        self.message_weights = {
            'order': 1.5,        # Информация о заказе
            'question': 1.2,     # Вопросы пользователя
            'preference': 1.2,   # Предпочтения пользователя
            'confirmation': 1.1, # Подтверждения
            'greeting': 0.5,     # Приветствия
            'default': 1.0       # По умолчанию
        }
        
        # Ключевые слова для определения типа сообщения
        self.message_type_keywords = {
            'order': [
                'заказ', 'купить', 'оформить', 'букет', 'розы',
                'доставка', 'оплата'
            ],
            'question': [
                'как', 'где', 'когда', 'сколько', 'почему',
                'какой', 'какая', 'какие'
            ],
            'preference': [
                'нравится', 'хочу', 'предпочитаю', 'люблю',
                'не люблю', 'красный', 'белый', 'розовый'
            ],
            'confirmation': [
                'да', 'нет', 'подтверждаю', 'согласен',
                'хорошо', 'ок', 'верно'
            ],
            'greeting': [
                'привет', 'здравствуйте', 'добрый день',
                'доброе утро', 'добрый вечер', 'пока', 'до свидания'
            ]
        }

    def _determine_message_type(self, message: str) -> str:
        """Определяет тип сообщения на основе его содержания."""
        message_lower = message.lower()
        
        for msg_type, keywords in self.message_type_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return msg_type
        return 'default'

    def _calculate_message_importance(self, message: Dict) -> float:
        """Вычисляет важность сообщения."""
        base_weight = self.message_weights.get(
            message['type'],
            self.message_weights['default']
        )
        
        # Учитываем время сообщения (более новые важнее)
        time_factor = 1.0
        if 'timestamp' in message:
            age = datetime.now() - datetime.fromtimestamp(message['timestamp'])
            time_factor = max(0.5, 1 - (age.total_seconds() / (self.message_ttl * 3600)))
        
        # Учитываем длину сообщения
        length_factor = min(1.5, len(message['content']) / 100)
        
        return base_weight * time_factor * length_factor

    def _cleanup_history(self, user_id: int) -> None:
        """Очищает историю от старых и неважных сообщений."""
        if user_id not in self.conversations:
            return
            
        # Удаляем сообщения старше TTL
        current_time = datetime.now().timestamp()
        ttl_threshold = current_time - (self.message_ttl * 3600)
        
        self.conversations[user_id] = [
            msg for msg in self.conversations[user_id]
            if msg['timestamp'] > ttl_threshold
        ]
        
        # Если всё ещё превышен лимит, удаляем наименее важные сообщения
        if len(self.conversations[user_id]) > self.max_history_size:
            # Сортируем по важности
            self.conversations[user_id].sort(
                key=lambda x: self._calculate_message_importance(x),
                reverse=True
            )
            # Оставляем только max_history_size самых важных сообщений
            self.conversations[user_id] = self.conversations[user_id][:self.max_history_size]

    async def add_message(self, user_id: int, content: str, role: str = 'user') -> None:
        """Добавляет новое сообщение в историю диалога."""
        try:
            message_type = self._determine_message_type(content)
            
            message = {
                'role': role,
                'content': content,
                'type': message_type,
                'timestamp': datetime.now().timestamp(),
                'created_at': datetime.now().isoformat()
            }
            
            self.conversations[user_id].append(message)
            self._cleanup_history(user_id)
            
            logger.info(f"Added message for user {user_id}, type: {message_type}")
            
        except Exception as e:
            logger.error(f"Error adding message to history: {e}")

    async def get_context(self, user_id: int, max_messages: int = None) -> List[Dict]:
        """Получает контекст диалога для пользователя."""
        try:
            if user_id not in self.conversations:
                return []
                
            # Очищаем старые сообщения
            self._cleanup_history(user_id)
            
            # Если указан лимит сообщений
            if max_messages:
                # Сортируем по важности и берем самые важные
                messages = sorted(
                    self.conversations[user_id],
                    key=lambda x: self._calculate_message_importance(x),
                    reverse=True
                )
                context = messages[:max_messages]
            else:
                context = self.conversations[user_id]
            
            # Преобразуем timestamp в строку ISO формата для JSON сериализации
            for message in context:
                if 'timestamp' in message:
                    message['timestamp'] = datetime.fromtimestamp(message['timestamp']).isoformat()
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context: {e}")
            return []

    async def get_relevant_context(self, user_id: int, current_message: str,
                                 max_messages: int = 5) -> List[Dict]:
        """Получает релевантный контекст на основе текущего сообщения."""
        try:
            if user_id not in self.conversations:
                return []
            
            current_type = self._determine_message_type(current_message)
            
            # Получаем все сообщения и вычисляем их релевантность
            relevant_messages = []
            for msg in self.conversations[user_id]:
                relevance = self._calculate_relevance(current_message, current_type, msg)
                relevant_messages.append((msg, relevance))
            
            # Сортируем по релевантности
            relevant_messages.sort(key=lambda x: x[1], reverse=True)
            
            # Берем только самые релевантные сообщения
            context = [msg for msg, _ in relevant_messages[:max_messages]]
            
            # Преобразуем timestamp в строку ISO формата для JSON сериализации
            for message in context:
                if 'timestamp' in message:
                    message['timestamp'] = datetime.fromtimestamp(message['timestamp']).isoformat()
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting relevant context: {e}")
            return []

    def _calculate_relevance(self, current_message: str, current_type: str,
                           historical_message: Dict) -> float:
        """Вычисляет релевантность исторического сообщения к текущему."""
        relevance = 0.0
        
        # Учитываем тип сообщения
        if historical_message['type'] == current_type:
            relevance += 1.0
        elif historical_message['type'] == 'order' and current_type == 'question':
            relevance += 0.8  # Вопросы о заказе важны
            
        # Учитываем временной фактор
        age = datetime.now().timestamp() - historical_message['timestamp']
        time_factor = max(0.2, 1 - (age / (self.message_ttl * 3600)))
        relevance *= time_factor
        
        # Учитываем текстовое сходство
        if self._has_common_keywords(current_message, historical_message['content']):
            relevance += 0.5
            
        return relevance

    def _has_common_keywords(self, message1: str, message2: str) -> bool:
        """Проверяет наличие общих ключевых слов в сообщениях."""
        # Простая проверка на общие слова (можно улучшить)
        words1 = set(message1.lower().split())
        words2 = set(message2.lower().split())
        common_words = words1.intersection(words2)
        
        # Исключаем общие слова
        stop_words = {'и', 'в', 'на', 'с', 'по', 'к', 'у', 'о', 'за'}
        meaningful_common_words = common_words - stop_words
        
        return len(meaningful_common_words) > 0

    async def clear_user_history(self, user_id: int) -> None:
        """Очищает историю диалога для пользователя."""
        if user_id in self.conversations:
            del self.conversations[user_id]
            logger.info(f"Cleared history for user {user_id}")

    def get_statistics(self, user_id: int) -> Dict:
        """Получает статистику диалога для пользователя."""
        if user_id not in self.conversations:
            return {}
            
        messages = self.conversations[user_id]
        
        return {
            'total_messages': len(messages),
            'message_types': {
                msg_type: len([m for m in messages if m['type'] == msg_type])
                for msg_type in self.message_weights.keys()
            },
            'avg_message_length': sum(len(m['content']) for m in messages) / len(messages),
            'first_message_time': datetime.fromtimestamp(
                min(m['timestamp'] for m in messages)
            ).isoformat(),
            'last_message_time': datetime.fromtimestamp(
                max(m['timestamp'] for m in messages)
            ).isoformat()
        }
