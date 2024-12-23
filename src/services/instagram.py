"""
Модуль для работы с Instagram API
Объединяет все функции для работы с Instagram в одном месте
"""
import os
import logging
from typing import Optional, Dict, Any

import requests
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class InstagramService:
    def __init__(self):
        """Инициализация сервиса Instagram"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def get_credentials(self) -> Dict[str, str]:
        """Получение учетных данных Instagram из базы"""
        try:
            response = self.supabase.table("credentials").select("*").eq("service_name", "instagram").execute()
            credentials = {}
            for record in response.data:
                credentials[record["credential_key"]] = record["credential_value"]
            return credentials
        except Exception as e:
            logger.error(f"Ошибка при получении учетных данных Instagram: {e}")
            raise

    def get_page_access_token(self, page_id: str) -> Optional[str]:
        """Получение токена доступа к странице Instagram"""
        try:
            credentials = self.get_credentials()
            access_token = credentials.get("access_token")
            
            if not access_token:
                logger.error("Токен доступа не найден")
                return None
                
            url = f"https://graph.facebook.com/v18.0/{page_id}"
            params = {
                "fields": "access_token",
                "access_token": access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json().get("access_token")
            
        except Exception as e:
            logger.error(f"Ошибка при получении токена страницы: {e}")
            return None

    def get_instagram_business_id(self, page_id: str) -> Optional[str]:
        """Получение ID бизнес-аккаунта Instagram"""
        try:
            credentials = self.get_credentials()
            access_token = credentials.get("access_token")
            
            if not access_token:
                logger.error("Токен доступа не найден")
                return None
                
            url = f"https://graph.facebook.com/v18.0/{page_id}"
            params = {
                "fields": "instagram_business_account",
                "access_token": access_token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json().get("instagram_business_account", {}).get("id")
            
        except Exception as e:
            logger.error(f"Ошибка при получении ID бизнес-аккаунта: {e}")
            return None

    def get_page_messages(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Получение сообщений страницы Instagram"""
        try:
            page_token = self.get_page_access_token(page_id)
            if not page_token:
                return None
                
            url = f"https://graph.facebook.com/v18.0/{page_id}/conversations"
            params = {
                "access_token": page_token,
                "fields": "messages{message,from,created_time}"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Ошибка при получении сообщений: {e}")
            return None

    def update_credentials(self, credentials: Dict[str, str]) -> bool:
        """Обновление учетных данных Instagram в базе"""
        try:
            # Сначала удаляем старые записи
            self.supabase.table("credentials").delete().eq("service_name", "instagram").execute()
            
            # Добавляем новые записи
            for key, value in credentials.items():
                self.supabase.table("credentials").insert({
                    "service_name": "instagram",
                    "credential_key": key,
                    "credential_value": value,
                    "description": f"Instagram {key}"
                }).execute()
                
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении учетных данных: {e}")
            return False

    def check_credentials(self) -> bool:
        """Проверка валидности учетных данных Instagram"""
        try:
            credentials = self.get_credentials()
            access_token = credentials.get("access_token")
            
            if not access_token:
                return False
                
            url = "https://graph.facebook.com/v18.0/me"
            params = {"access_token": access_token}
            
            response = requests.get(url, params=params)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Ошибка при проверке учетных данных: {e}")
            return False
