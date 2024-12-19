import logging
import re
import time
from collections import defaultdict
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        # Основной кэш для хранения ответов
        self.cache: Dict[str, Dict[str, Any]] = {}
        # Счетчик частоты запросов
        self.frequency = defaultdict(int)
        # Время жизни кэша в секундах (1 час)
        self.ttl = 3600
        # Минимальное количество запросов для кэширования
        self.min_frequency = 3
        # Максимальный размер кэша
        self.max_cache_size = 1000

    def _normalize_query(self, query: str) -> str:
        """
        Нормализует запрос для лучшего matching:
        - приводит к нижнему регистру
        - удаляет лишние пробелы
        - удаляет пунктуацию
        """
        # Приводим к нижнему регистру и удаляем лишние пробелы
        normalized = re.sub(r'\s+', ' ', query.lower().strip())
        # Удаляем пунктуацию, кроме важных символов
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized

    def _is_similar_query(self, query1: str, query2: str, threshold: float = 0.8) -> bool:
        """
        Проверяет, являются ли запросы похожими.
        Использует простое сравнение множеств слов.
        """
        words1 = set(query1.split())
        words2 = set(query2.split())
        
        if not words1 or not words2:
            return False
            
        intersection = words1.intersection(words2)
        shorter_len = min(len(words1), len(words2))
        
        similarity = len(intersection) / shorter_len
        return similarity >= threshold

    async def get_cached_response(self, query: str) -> Optional[str]:
        """
        Получает кэшированный ответ для запроса.
        Также обновляет счетчик частоты.
        """
        normalized_query = self._normalize_query(query)
        current_time = time.time()

        # Проверяем точное совпадение
        if normalized_query in self.cache:
            cache_entry = self.cache[normalized_query]
            # Проверяем не истек ли TTL
            if current_time - cache_entry['timestamp'] < self.ttl:
                self.frequency[normalized_query] += 1
                logger.info(f"Cache hit for query: {query}")
                return cache_entry['response']
            else:
                # Удаляем устаревшую запись
                del self.cache[normalized_query]
                logger.info(f"Removed expired cache entry for query: {query}")

        # Проверяем похожие запросы
        for cached_query in list(self.cache.keys()):
            if self._is_similar_query(normalized_query, cached_query):
                cache_entry = self.cache[cached_query]
                if current_time - cache_entry['timestamp'] < self.ttl:
                    self.frequency[cached_query] += 1
                    logger.info(f"Cache hit for similar query: {query} -> {cached_query}")
                    return cache_entry['response']
                else:
                    del self.cache[cached_query]
                    logger.info(f"Removed expired cache entry for similar query: {cached_query}")

        # Увеличиваем счетчик частоты для нового запроса
        self.frequency[normalized_query] += 1
        return None

    async def cache_response(self, query: str, response: str) -> None:
        """
        Кэширует ответ для запроса, если он достаточно частый.
        """
        normalized_query = self._normalize_query(query)
        
        # Кэшируем только если запрос встречается достаточно часто
        if self.frequency[normalized_query] >= self.min_frequency:
            # Проверяем размер кэша
            if len(self.cache) >= self.max_cache_size:
                # Удаляем наименее частые запросы
                sorted_queries = sorted(
                    self.frequency.items(),
                    key=lambda x: x[1]
                )
                for old_query, _ in sorted_queries[:len(self.cache) - self.max_cache_size + 1]:
                    if old_query in self.cache:
                        del self.cache[old_query]
                        logger.info(f"Removed least frequent cache entry: {old_query}")

            # Добавляем новую запись в кэш
            self.cache[normalized_query] = {
                'response': response,
                'timestamp': time.time()
            }
            logger.info(f"Added new cache entry for query: {query}")

    async def clear_expired(self) -> None:
        """
        Очищает устаревшие записи из кэша.
        """
        current_time = time.time()
        expired_queries = [
            query for query, entry in self.cache.items()
            if current_time - entry['timestamp'] >= self.ttl
        ]
        
        for query in expired_queries:
            del self.cache[query]
            logger.info(f"Cleared expired cache entry: {query}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику использования кэша.
        """
        return {
            'total_entries': len(self.cache),
            'frequency_stats': dict(self.frequency),
            'cache_size': len(self.cache),
            'most_frequent': sorted(
                self.frequency.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
