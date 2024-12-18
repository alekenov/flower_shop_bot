import os
import logging
from psycopg2.extras import DictCursor, Json
from typing import List, Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv
from .database_service import database_service

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseService, cls).__new__(cls)
        return cls._instance

    def get_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get products from database, optionally filtered by category."""
        try:
            if category:
                return database_service.execute_query(
                    "SELECT * FROM products WHERE category = %s", 
                    (category,)
                )
            else:
                return database_service.execute_query("SELECT * FROM products")
        except Exception as e:
            logger.error(f"Failed to get products: {str(e)}")
            return []

    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a product by its name."""
        try:
            return database_service.execute_query_single(
                "SELECT * FROM products WHERE name ILIKE %s", 
                (f"%{name}%",)
            )
        except Exception as e:
            logger.error(f"Failed to get product by name: {str(e)}")
            return None

    def save_conversation(self, user_id: int, message: str, response: str) -> None:
        """Save conversation history."""
        try:
            database_service.execute_query(
                """
                INSERT INTO conversations (user_id, message, response, created_at)
                VALUES (%s, %s, %s, %s)
                """, 
                (user_id, message, response, datetime.utcnow()),
                fetch=False
            )
        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}")

    def get_user_preferences(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        try:
            return database_service.execute_query_single(
                "SELECT * FROM user_preferences WHERE user_id = %s", 
                (user_id,)
            )
        except Exception as e:
            logger.error(f"Failed to get user preferences: {str(e)}")
            return None

    def update_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> None:
        """Update user preferences."""
        try:
            existing = self.get_user_preferences(user_id)
            if existing:
                # Подготовка данных для обновления
                set_clause = ", ".join([f"{k} = %s" for k in preferences.keys()])
                values = list(preferences.values())
                values.append(user_id)
                database_service.execute_query(
                    f"UPDATE user_preferences SET {set_clause} WHERE user_id = %s",
                    tuple(values),
                    fetch=False
                )
            else:
                # Подготовка данных для вставки
                columns = ["user_id"] + list(preferences.keys())
                placeholders = ["%s"] * (len(preferences) + 1)
                values = [user_id] + list(preferences.values())
                database_service.execute_query(
                    f"""
                    INSERT INTO user_preferences ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    """,
                    tuple(values),
                    fetch=False
                )
        except Exception as e:
            logger.error(f"Failed to update user preferences: {str(e)}")

    def save_user_insight(self, user_id: int, insight_type: str, data: Dict[str, Any]) -> None:
        """Save user insight."""
        try:
            database_service.execute_query(
                """
                INSERT INTO user_insights (user_id, type, data, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, insight_type, Json(data), datetime.utcnow()),
                fetch=False
            )
        except Exception as e:
            logger.error(f"Failed to save user insight: {str(e)}")

    def get_conversation_context(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation context for a user."""
        try:
            return database_service.execute_query(
                """
                SELECT message, response, created_at
                FROM conversations
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit)
            )
        except Exception as e:
            logger.error(f"Failed to get conversation context: {str(e)}")
            return []

    def save_interaction_pattern(self, user_id: int, pattern_type: str, data: Dict[str, Any]) -> None:
        """Save interaction pattern."""
        try:
            database_service.execute_query(
                """
                INSERT INTO interaction_patterns (user_id, type, data, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, pattern_type, Json(data), datetime.utcnow()),
                fetch=False
            )
        except Exception as e:
            logger.error(f"Failed to save interaction pattern: {str(e)}")

    def update_product_quantity(self, product_name: str, quantity_change: int) -> bool:
        """Update product quantity. Positive value to add, negative to subtract."""
        try:
            # First get current quantity
            result = database_service.execute_query_single(
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
            
            # Update quantity
            database_service.execute_query(
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

    def get_service_account(self, account_name: str) -> Optional[Dict[str, Any]]:
        """
        Получить данные сервисного аккаунта из базы данных
        
        Args:
            account_name: Имя сервисного аккаунта
            
        Returns:
            Словарь с данными сервисного аккаунта или None, если не найден
        """
        try:
            return database_service.execute_query_single(
                """
                SELECT credential_value
                FROM credentials
                WHERE service_name = 'google'
                AND credential_key = %s
                """,
                (account_name,)
            )
        except Exception as e:
            logger.error(f"Failed to get service account {account_name}: {str(e)}")
            return None

    def save_service_account(self, credentials: Dict[str, Any], account_name: str) -> bool:
        """
        Сохранить данные сервисного аккаунта в базу данных
        
        Args:
            credentials: Словарь с данными сервисного аккаунта
            account_name: Имя сервисного аккаунта
            
        Returns:
            True если сохранение успешно, False в противном случае
        """
        try:
            database_service.execute_query(
                """
                INSERT INTO credentials (service_name, credential_key, credential_value, description)
                VALUES ('google', %s, %s, 'Google service account credentials')
                ON CONFLICT (service_name, credential_key) 
                DO UPDATE SET 
                    credential_value = EXCLUDED.credential_value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (account_name, Json(credentials)),
                fetch=False
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save service account {account_name}: {str(e)}")
            return False

# Create a global instance
supabase_service = SupabaseService()
