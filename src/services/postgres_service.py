import asyncpg
import logging
import json
from typing import Optional, List, Any, Dict
from utils.logger_config import get_logger
import psycopg2
from psycopg2.extras import DictCursor
from .bootstrap_config import BOOTSTRAP_DB_URL
from datetime import datetime
import pytz

logger = get_logger('postgres_service')

class PostgresService:
    def __init__(self):
        self.pool = None
        self.db_url = None
        
    def _get_connection_params(self) -> Dict[str, str]:
        """Получение параметров подключения из базы данных"""
        try:
            # Используем bootstrap URL для первого подключения
            conn = psycopg2.connect(BOOTSTRAP_DB_URL)
            conn.autocommit = True
            
            cur = conn.cursor(cursor_factory=DictCursor)
            cur.execute("""
                SELECT credential_key, credential_value 
                FROM credentials 
                WHERE service_name = 'supabase' 
                AND credential_key LIKE 'db_%'
            """)
            
            params = {row['credential_key']: row['credential_value'] for row in cur.fetchall()}
            cur.close()
            conn.close()
            
            return params
            
        except Exception as e:
            logger.error(f"Failed to get connection parameters: {e}")
            raise

    async def connect(self):
        """Создание пула соединений"""
        if not self.pool:
            try:
                if not self.db_url:
                    params = self._get_connection_params()
                    self.db_url = f"postgresql://{params['db_user']}:{params['db_password']}@{params['db_host']}:{params['db_port']}/{params['db_name']}"
                
                # Отключаем prepared statements для работы с pgbouncer
                self.pool = await asyncpg.create_pool(
                    self.db_url,
                    statement_cache_size=0
                )
                logger.info("Successfully connected to database")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise

    async def fetch_one(self, query: str, *args) -> Optional[Dict]:
        """Получение одной записи"""
        if not self.pool:
            await self.connect()
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error in fetch_one: {e}")
            return None

    async def fetch_all(self, query: str, *args) -> List[Dict]:
        """Получение всех записей"""
        if not self.pool:
            await self.connect()
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error in fetch_all: {e}")
            return []

    async def execute(self, query: str, *args) -> bool:
        """Выполнение запроса"""
        if not self.pool:
            await self.connect()
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, *args)
                return True
        except Exception as e:
            logger.error(f"Error in execute: {e}")
            return False

    async def close(self):
        """Закрытие соединений"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def save_to_cache(self, source: str, data: dict) -> bool:
        """Сохранение данных в кэш"""
        query = """
            INSERT INTO data_cache (source, data) 
            VALUES ($1, $2)
        """
        return await self.execute(query, source, json.dumps(data))

    async def get_from_cache(self, source: str, max_age_seconds: int = 3600) -> Optional[dict]:
        """Получение данных из кэша если они не старше max_age_seconds"""
        query = """
            SELECT data, last_update
            FROM data_cache 
            WHERE source = $1 
            ORDER BY last_update DESC 
            LIMIT 1
        """
        result = await self.fetch_one(query, source)
        
        if not result:
            return None
            
        # Проверяем возраст данных
        age = (datetime.now(pytz.utc) - result['last_update']).total_seconds()
        if age > max_age_seconds:
            return None
            
        return json.loads(result['data'])

    async def clear_cache(self, source: Optional[str] = None) -> bool:
        """Очистка кэша. Если source не указан - очищает весь кэш"""
        if source:
            query = "DELETE FROM data_cache WHERE source = $1"
            return await self.execute(query, source)
        else:
            query = "DELETE FROM data_cache"
            return await self.execute(query)
