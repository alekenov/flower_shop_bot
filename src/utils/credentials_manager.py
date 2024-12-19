import logging
import psycopg2
import psycopg2.extras
import json
import os
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class CredentialsManager:
    def __init__(self):
        """Initialize database connection."""
        try:
            # Подключение к базе данных
            self.conn = psycopg2.connect(
                host="aws-0-eu-central-1.pooler.supabase.com",
                port=6543,
                database="postgres",
                user="postgres.dkohweivbdwweyvyvcbc",
                password=os.environ.get('SUPABASE_DB_PASSWORD'),
                sslmode='require'
            )
            self.conn.autocommit = True
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            raise

    def get_credentials(self, service_name: str) -> Dict[str, str]:
        """
        Get all credentials for a specific service
        
        Args:
            service_name (str): Name of the service (e.g., 'telegram', 'openai')
            
        Returns:
            Dict[str, str]: Dictionary of credential_key: credential_value pairs
        """
        try:
            query = """
                SELECT credential_key, credential_value 
                FROM credentials 
                WHERE service_name = %s
            """
            logger.info(f"Executing query: {query} with params: {service_name}")
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, (service_name,))
                results = cur.fetchall()
                
                if not results:
                    logger.warning(f"Не найдены учетные данные для сервиса {service_name}")
                    return {}
                
                # Создаем словарь учетных данных
                credentials = {}
                for row in results:
                    credentials[row['credential_key']] = row['credential_value']
                
                return credentials
                
        except Exception as e:
            logger.error(f"Ошибка при получении учетных данных: {str(e)}")
            return {}

    def get_credential(self, service_name: str, credential_key: str) -> Optional[str]:
        """
        Get a specific credential value
        
        Args:
            service_name (str): Name of the service (e.g., 'telegram', 'openai')
            credential_key (str): Key of the credential (e.g., 'api_key', 'bot_token')
            
        Returns:
            Optional[str]: Credential value if found, None otherwise
        """
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    """
                    SELECT credential_value 
                    FROM credentials 
                    WHERE service_name = %s AND credential_key = %s
                    """, 
                    (service_name, credential_key)
                )
                result = cur.fetchone()
                
                if not result:
                    logger.warning(f"Не найдены учетные данные {credential_key} для сервиса {service_name}")
                    return None
                
                return result['credential_value']
                
        except Exception as e:
            logger.error(f"Ошибка при получении учетных данных: {str(e)}")
            return None

    def set_credential(self, service_name: str, credential_key: str, credential_value: str, description: str = "") -> bool:
        """
        Set a credential value
        
        Args:
            service_name (str): Name of the service
            credential_key (str): Key of the credential
            credential_value (str): Value of the credential
            description (str): Optional description
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO credentials (service_name, credential_key, credential_value, description)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (service_name, credential_key) 
                    DO UPDATE SET 
                        credential_value = EXCLUDED.credential_value,
                        description = EXCLUDED.description
                    """,
                    (service_name, credential_key, credential_value, description)
                )
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении учетных данных: {str(e)}")
            return False

    def __del__(self):
        """Close database connection on cleanup"""
        try:
            self.conn.close()
        except:
            pass

# Create a singleton instance
credentials_manager = CredentialsManager()
