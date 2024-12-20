import logging
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import DictCursor
import os

logger = logging.getLogger(__name__)

# Конфигурация подключения к Supabase
SUPABASE_CONFIG = {
    'host': 'aws-0-eu-central-1.pooler.supabase.com',
    'port': '6543',
    'user': 'postgres.dkohweivbdwweyvyvcbc',
    'password': 'vigkif-nesJy2-kivraq',
    'database': 'postgres'
}

class ConfigService:
    """
    Сервис для работы с конфигурацией и учетными данными в Supabase.
    Реализует паттерн Singleton для обеспечения единственного подключения к БД.
    Использует кэширование для оптимизации производительности.
    """
    
    _instance = None
    _credentials_cache: Dict[str, Dict[str, str]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigService, cls).__new__(cls)
            cls._instance._init_connection()
            cls._instance._init_cache()
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
    
    def _init_cache(self) -> None:
        """Инициализация кэша учетных данных"""
        self._credentials_cache = {}
    
    def _get_service_credentials(self, service: str) -> Dict[str, str]:
        """
        Получение учетных данных сервиса с кэшированием
        
        Args:
            service: Название сервиса
            
        Returns:
            Dict[str, str]: Словарь с учетными данными
        """
        if service not in self._credentials_cache:
            try:
                with self.conn.cursor(cursor_factory=DictCursor) as cur:
                    cur.execute(
                        """
                        SELECT credential_key, credential_value
                        FROM credentials
                        WHERE service_name = %s
                        """,
                        (service,)
                    )
                    results = cur.fetchall()
                    self._credentials_cache[service] = {
                        row['credential_key']: row['credential_value']
                        for row in results
                    }
            except Exception as e:
                logger.error(f"Failed to get credentials for service {service}: {str(e)}")
                self._credentials_cache[service] = {}
                
        return self._credentials_cache[service]
    
    def get_config(self, key: str, required: bool = False) -> Optional[str]:
        """
        Получение значения конфигурации по ключу
        
        Args:
            key: Ключ конфигурации в формате 'SERVICE_KEY'
            required: Является ли значение обязательным
            
        Returns:
            Optional[str]: Значение конфигурации
            
        Raises:
            ValueError: Если required=True и значение не найдено
            ValueError: Если формат ключа неверный
        """
        try:
            # Разбираем ключ на сервис и ключ учетных данных
            parts = key.lower().split('_', 1)
            if len(parts) != 2:
                msg = f"Invalid config key format: {key}. Expected format: 'SERVICE_KEY'"
                if required:
                    raise ValueError(msg)
                logger.error(msg)
                return None
                
            service_name, credential_key = parts
            
            # Получаем значение из кэша
            creds = self._get_service_credentials(service_name)
            value = creds.get(credential_key)
            
            if value is None:
                msg = f"Config value not found for key: {key}"
                if required:
                    raise ValueError(msg)
                logger.warning(msg)
            
            return value
            
        except Exception as e:
            msg = f"Error getting config for key {key}: {str(e)}"
            if required:
                raise ValueError(msg)
            logger.error(msg)
            return None
    
    def set_config(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """
        Установка значения конфигурации
        
        Args:
            key: Ключ конфигурации в формате 'SERVICE_KEY'
            value: Значение конфигурации
            description: Описание (опционально)
            
        Returns:
            bool: True если успешно, False в противном случае
        """
        try:
            # Разбираем ключ на сервис и ключ учетных данных
            parts = key.lower().split('_', 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid config key format: {key}. Expected format: 'SERVICE_KEY'")
                
            service_name, credential_key = parts
            
            # Обновляем значение в базе данных
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO credentials (service_name, credential_key, credential_value, description)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (service_name, credential_key) 
                    DO UPDATE SET 
                        credential_value = EXCLUDED.credential_value,
                        description = EXCLUDED.description,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (service_name, credential_key, value, description)
                )
            
            # Инвалидируем кэш для этого сервиса
            self.invalidate_cache(service_name)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set config {key}: {str(e)}")
            return False
    
    def invalidate_cache(self, service: Optional[str] = None) -> None:
        """
        Инвалидация кэша учетных данных
        
        Args:
            service: Название сервиса для инвалидации.
                    Если None, инвалидируется весь кэш.
        """
        if service:
            self._credentials_cache.pop(service, None)
        else:
            self._credentials_cache.clear()
    
    def __del__(self):
        """Закрытие соединения при удалении объекта"""
        try:
            if hasattr(self, 'conn'):
                self.conn.close()
        except:
            pass

# Создаем глобальный экземпляр сервиса
config_service = ConfigService()
