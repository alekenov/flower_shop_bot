import logging
import re
import time
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.db = SupabaseService()
        self.similarity_threshold = 0.8

    def _normalize_query(self, query: str) -> str:
        """Нормализует запрос для лучшего matching"""
        normalized = re.sub(r'\s+', ' ', query.lower().strip())
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized

    def _generate_hash(self, query: str) -> str:
        """Генерирует хеш для запроса"""
        return hashlib.md5(query.encode()).hexdigest()

    def _is_similar_query(self, query1: str, query2: str) -> bool:
        """Проверяет схожесть запросов"""
        words1 = set(query1.split())
        words2 = set(query2.split())
        
        if not words1 or not words2:
            return False
            
        intersection = words1.intersection(words2)
        shorter_len = min(len(words1), len(words2))
        
        similarity = len(intersection) / shorter_len
        return similarity >= self.similarity_threshold

    async def get_cached_response(self, query: str) -> Optional[Dict[str, Any]]:
        """Получает кэшированный ответ из БД"""
        normalized = self._normalize_query(query)
        query_hash = self._generate_hash(normalized)

        # Поиск точного совпадения
        result = self.db.execute_query_single(
            """
            SELECT * FROM cache_answers 
            WHERE question_hash = %s
            """, 
            (query_hash,)
        )

        if not result:
            # Поиск похожих вопросов
            similar_questions = self.db.execute_query(
                """
                SELECT * FROM cache_answers
                """,
            )
            for cached in similar_questions:
                if self._is_similar_query(normalized, self._normalize_query(cached['question'])):
                    result = cached
                    break

        if result:
            # Обновляем счетчик использования
            self.db.execute_query(
                """
                UPDATE cache_answers 
                SET hits = hits + 1 
                WHERE question_hash = %s
                """,
                (result['question_hash'],),
                fetch=False
            )
            return result

        return None

    async def cache_response(self, query: str, answer: str) -> None:
        """Сохраняет ответ в кэш"""
        normalized = self._normalize_query(query)
        query_hash = self._generate_hash(normalized)

        self.db.execute_query(
            """
            INSERT INTO cache_answers (question_hash, question, answer)
            VALUES (%s, %s, %s)
            ON CONFLICT (question_hash) 
            DO UPDATE SET 
                answer = EXCLUDED.answer,
                last_updated = NOW()
            """,
            (query_hash, query, answer),
            fetch=False
        )

    async def log_interaction(
        self, 
        user_id: int, 
        question: str, 
        answer: str, 
        response_time: int,
        was_cached: bool
    ) -> None:
        """Логирует взаимодействие с пользователем"""
        self.db.execute_query(
            """
            INSERT INTO chat_statistics 
            (user_id, question, answer, response_time_ms, was_cached)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, question, answer, response_time, was_cached),
            fetch=False
        )

    async def update_feedback(self, question: str, was_helpful: bool) -> None:
        """Обновляет обратную связь по ответу"""
        normalized = self._normalize_query(question)
        query_hash = self._generate_hash(normalized)

        feedback_field = 'positive_feedback' if was_helpful else 'negative_feedback'
        self.db.execute_query(
            f"""
            UPDATE cache_answers 
            SET {feedback_field} = {feedback_field} + 1
            WHERE question_hash = %s
            """,
            (query_hash,),
            fetch=False
        )

    async def get_or_create_context(self, user_id: int) -> Dict[str, Any]:
        """Получает или создает контекст диалога"""
        context = self.db.execute_query_single(
            """
            SELECT context FROM chat_context
            WHERE user_id = %s
            """,
            (user_id,)
        )

        if not context:
            context = {'messages': []}
            self.db.execute_query(
                """
                INSERT INTO chat_context (user_id, context)
                VALUES (%s, %s)
                """,
                (user_id, context),
                fetch=False
            )

        return context

    async def update_context(self, user_id: int, context: Dict[str, Any]) -> None:
        """Обновляет контекст диалога"""
        self.db.execute_query(
            """
            UPDATE chat_context 
            SET context = %s, last_updated = NOW()
            WHERE user_id = %s
            """,
            (context, user_id),
            fetch=False
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику использования"""
        stats = {
            'popular_questions': self.db.execute_query(
                """
                SELECT question, hits 
                FROM cache_answers 
                ORDER BY hits DESC 
                LIMIT 5
                """
            ),
            'response_times': self.db.execute_query(
                """
                SELECT 
                    AVG(response_time_ms) as avg_time,
                    MIN(response_time_ms) as min_time,
                    MAX(response_time_ms) as max_time
                FROM chat_statistics
                """
            )[0],
            'cache_effectiveness': self.db.execute_query(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN was_cached THEN 1 ELSE 0 END) as cached
                FROM chat_statistics
                """
            )[0]
        }
        return stats
