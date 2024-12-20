import os
import logging
import psycopg2
from psycopg2.extras import DictCursor, Json
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# Конфигурация подключения к Supabase
SUPABASE_CONFIG = {
    'host': 'aws-0-eu-central-1.pooler.supabase.com',
    'port': '6543',
    'user': 'postgres.dkohweivbdwweyvyvcbc',
    'password': 'vigkif-nesJy2-kivraq',
    'database': 'postgres'
}

class SupabaseService:
    """
    Сервис для работы с базой данных Supabase.
    Реализует паттерн Singleton для обеспечения единственного подключения к БД.
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseService, cls).__new__(cls)
            cls._instance._init_connection()
        return cls._instance

    def _init_connection(self) -> None:
        """Инициализация подключения к базе данных"""
        try:
            # Подключаемся к базе данных используя прямые параметры
            self.conn = psycopg2.connect(
                host=SUPABASE_CONFIG['host'],
                port=SUPABASE_CONFIG['port'],
                user=SUPABASE_CONFIG['user'],
                password=SUPABASE_CONFIG['password'],
                database=SUPABASE_CONFIG['database']
            )
            self.conn.autocommit = True
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise

    def execute_query(
        self, 
        query: str, 
        params: Optional[Union[tuple, Dict[str, Any]]] = None,
        fetch: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Выполнение SQL запроса
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            fetch: Нужно ли возвращать результаты
            
        Returns:
            Список результатов или None
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    results = cur.fetchall()
                    return [dict(row) for row in results]
                return None
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            return None

    def execute_query_single(
        self, 
        query: str, 
        params: Optional[Union[tuple, Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Выполнение SQL запроса с возвратом одной строки
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            
        Returns:
            Словарь с результатом или None
        """
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query, params)
                result = cur.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to execute query: {str(e)}")
            return None

    # Методы для работы с продуктами
    def get_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение списка продуктов
        
        Args:
            category: Категория продуктов (опционально)
            
        Returns:
            Список продуктов
        """
        query = "SELECT * FROM products"
        params = None
        
        if category:
            query += " WHERE category = %s"
            params = (category,)
            
        return self.execute_query(query, params) or []

    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Поиск продукта по названию
        
        Args:
            name: Название продукта
            
        Returns:
            Информация о продукте или None
        """
        return self.execute_query_single(
            "SELECT * FROM products WHERE name ILIKE %s",
            (f"%{name}%",)
        )

    def update_product_quantity(self, product_name: str, quantity_change: int) -> bool:
        """
        Обновление количества продукта
        
        Args:
            product_name: Название продукта
            quantity_change: Изменение количества (положительное - добавить, отрицательное - убавить)
            
        Returns:
            True если обновление успешно, False в противном случае
        """
        try:
            # Проверяем текущее количество
            result = self.execute_query_single(
                "SELECT quantity FROM products WHERE name = %s",
                (product_name,)
            )
            
            if not result:
                logger.error(f"Product {product_name} not found")
                return False
            
            current_quantity = result['quantity']
            new_quantity = current_quantity + quantity_change
            
            if new_quantity < 0:
                logger.error(f"Cannot reduce quantity below 0 for {product_name}")
                return False
            
            # Обновляем количество
            self.execute_query(
                """
                UPDATE products 
                SET quantity = %s 
                WHERE name = %s
                """,
                (new_quantity, product_name),
                fetch=False
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to update product quantity: {str(e)}")
            return False

    # Методы для работы с историей разговоров
    def save_conversation(
        self, 
        user_id: int, 
        message: str, 
        response: str
    ) -> None:
        """
        Сохранение истории разговора
        
        Args:
            user_id: ID пользователя
            message: Сообщение пользователя
            response: Ответ бота
        """
        self.execute_query(
            """
            INSERT INTO conversations (user_id, message, response, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, message, response, datetime.now()),
            fetch=False
        )

    def get_conversation_context(
        self, 
        user_id: int, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Получение контекста разговора
        
        Args:
            user_id: ID пользователя
            limit: Количество последних сообщений
            
        Returns:
            Список сообщений
        """
        return self.execute_query(
            """
            SELECT message, response, created_at
            FROM conversations
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit)
        ) or []

    def __del__(self):
        """Закрытие соединения при удалении объекта"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except:
            pass

# Создаем глобальный экземпляр
supabase_service = SupabaseService()
