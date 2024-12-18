import os
import logging
from typing import Optional, Dict, Union, Any
import psycopg2
from psycopg2.extras import DictCursor, Json
import json

logger = logging.getLogger(__name__)

class CredentialsService:
    _instance = None
    _credentials_cache: Dict[str, Dict[str, str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CredentialsService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # Инициализация подключения к базе данных
        self.conn = psycopg2.connect(
            dbname="postgres",
            user="postgres.dkohweivbdwweyvyvcbc",
            password="vigkif-nesJy2-kivraq",
            host="aws-0-eu-central-1.pooler.supabase.com",
            port="6543"
        )
        self._initialized = True
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Загрузка всех учетных данных из базы данных в кэш"""
        try:
            with self.conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT service_name, credential_key, credential_value 
                    FROM credentials
                """)
                rows = cur.fetchall()
                
                # Очищаем текущий кэш
                self._credentials_cache.clear()
                
                # Заполняем кэш новыми данными
                for row in rows:
                    service = row['service_name']
                    if service not in self._credentials_cache:
                        self._credentials_cache[service] = {}
                    
                    # Если значение - JSON, преобразуем его в словарь
                    value = row['credential_value']
                    if isinstance(value, str) and value.startswith('{'):
                        try:
                            value = json.loads(value)
                        except:
                            pass
                            
                    self._credentials_cache[service][row['credential_key']] = value
                
                logger.info(f"Loaded credentials for services: {list(self._credentials_cache.keys())}")
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            raise

    def get_credential(self, service_name: str, credential_key: str) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Получение значения учетных данных по имени сервиса и ключу
        
        Args:
            service_name: Имя сервиса (например, 'telegram', 'openai')
            credential_key: Ключ учетных данных (например, 'bot_token', 'api_key')
            
        Returns:
            Значение учетных данных или None, если не найдено
        """
        try:
            return self._credentials_cache[service_name][credential_key]
        except KeyError:
            # Если данных нет в кэше, пробуем перезагрузить их
            self._load_credentials()
            try:
                return self._credentials_cache[service_name][credential_key]
            except KeyError:
                logger.error(f"Credential not found: {service_name}.{credential_key}")
                return None

    def update_credential(self, service_name: str, credential_key: str, 
                        credential_value: Union[str, Dict[str, Any]], description: Optional[str] = None) -> bool:
        """
        Обновление значения учетных данных
        
        Args:
            service_name: Имя сервиса
            credential_key: Ключ учетных данных
            credential_value: Новое значение (строка или словарь)
            description: Описание (опционально)
            
        Returns:
            True если обновление успешно, False в противном случае
        """
        try:
            # Если значение - словарь, конвертируем его в JSON
            if isinstance(credential_value, dict):
                credential_value = json.dumps(credential_value)
                
            with self.conn.cursor() as cur:
                if description:
                    cur.execute("""
                        INSERT INTO credentials (service_name, credential_key, credential_value, description)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (service_name, credential_key) 
                        DO UPDATE SET 
                            credential_value = EXCLUDED.credential_value,
                            description = EXCLUDED.description,
                            updated_at = CURRENT_TIMESTAMP
                    """, (service_name, credential_key, credential_value, description))
                else:
                    cur.execute("""
                        INSERT INTO credentials (service_name, credential_key, credential_value)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (service_name, credential_key) 
                        DO UPDATE SET 
                            credential_value = EXCLUDED.credential_value,
                            updated_at = CURRENT_TIMESTAMP
                    """, (service_name, credential_key, credential_value))
                
                self.conn.commit()
                
                # Обновляем кэш
                if service_name not in self._credentials_cache:
                    self._credentials_cache[service_name] = {}
                    
                # Если значение было JSON строкой, преобразуем обратно в словарь
                value = credential_value
                if isinstance(value, str) and value.startswith('{'):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                        
                self._credentials_cache[service_name][credential_key] = value
                
                logger.info(f"Updated credential: {service_name}.{credential_key}")
                return True
        except Exception as e:
            logger.error(f"Error updating credential {service_name}.{credential_key}: {str(e)}")
            self.conn.rollback()
            return False

    def __del__(self):
        """Закрытие соединения с базой данных при уничтожении объекта"""
        if hasattr(self, 'conn'):
            self.conn.close()

# Создаем глобальный экземпляр сервиса
credentials_service = CredentialsService()
