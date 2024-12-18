import os
import logging
import psycopg2
from psycopg2.extras import DictCursor
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения для первоначального подключения
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseService:
    _instance = None
    _conn = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self._connect_initial()

    def _get_connection_params(self) -> dict:
        """
        Получение параметров подключения.
        Сначала пытаемся получить из переменных окружения,
        затем из credentials_service (если он уже инициализирован)
        """
        try:
            # Пробуем импортировать credentials_service только если он уже инициализирован
            from .credentials_service import credentials_service
            
            # Проверяем, что credentials_service полностью инициализирован
            if hasattr(credentials_service, '_initialized') and credentials_service._initialized:
                return {
                    'dbname': credentials_service.get_credential('supabase', 'db_name'),
                    'user': credentials_service.get_credential('supabase', 'db_user'),
                    'password': credentials_service.get_credential('supabase', 'db_password'),
                    'host': credentials_service.get_credential('supabase', 'db_host'),
                    'port': credentials_service.get_credential('supabase', 'db_port')
                }
        except (ImportError, AttributeError):
            pass
        
        # Если не удалось получить из credentials_service, используем переменные окружения
        return {
            'dbname': os.getenv('SUPABASE_DB_NAME', 'postgres'),
            'user': os.getenv('SUPABASE_DB_USER', 'postgres'),
            'password': os.getenv('SUPABASE_DB_PASSWORD'),
            'host': os.getenv('SUPABASE_DB_HOST'),
            'port': os.getenv('SUPABASE_DB_PORT', '5432')
        }

    def _connect_initial(self):
        """Первоначальное подключение к базе данных"""
        try:
            params = self._get_connection_params()
            if not all(params.values()):
                raise ValueError("Missing required database connection parameters")
                
            self._conn = psycopg2.connect(**params)
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise

    def _connect(self):
        """Переподключение к базе данных с актуальными параметрами"""
        try:
            params = self._get_connection_params()
            if not all(params.values()):
                raise ValueError("Missing required database connection parameters")
                
            self._conn = psycopg2.connect(**params)
            logger.info("Successfully reconnected to database")
        except Exception as e:
            logger.error(f"Error reconnecting to database: {str(e)}")
            raise

    def get_connection(self):
        """Получение соединения с базой данных"""
        if self._conn is None or self._conn.closed:
            self._connect()
        return self._conn

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[list]:
        """
        Выполнение SQL запроса
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            fetch: Нужно ли получать результат
            
        Returns:
            Результат запроса или None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    if fetch:
                        return cur.fetchall()
                    conn.commit()
                    return None
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            if not fetch:
                conn.rollback()
            raise

    def execute_query_single(self, query: str, params: tuple = None) -> Optional[dict]:
        """
        Выполнение SQL запроса с получением одной строки
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            
        Returns:
            Одна строка результата или None
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(query, params)
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise

    def __del__(self):
        """Закрытие соединения при уничтожении объекта"""
        if hasattr(self, '_conn') and self._conn is not None:
            self._conn.close()

# Создаем глобальный экземпляр сервиса
database_service = DatabaseService()
