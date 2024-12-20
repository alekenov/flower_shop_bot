#!/usr/bin/env python3

import argparse
import logging
import sys
import os
from typing import Optional, Dict, Any
import requests
from datetime import datetime

# Добавляем путь к корневой директории проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
# Устанавливаем PYTHONPATH
os.environ['PYTHONPATH'] = project_root

from src.utils.credentials_manager import credentials_manager
from src.utils.logger import setup_logger

logger = logging.getLogger(__name__)

class InstagramManager:
    """Менеджер для работы с Instagram API"""
    
    def __init__(self):
        """Инициализация менеджера"""
        self.credentials = credentials_manager.get_credentials('instagram')
        self.access_token = self.credentials.get('access_token')
        self.page_id = self.credentials.get('page_id')
        self.business_account_id = self.credentials.get('business_account_id')
        
        if not all([self.access_token, self.page_id]):
            raise ValueError("Не найдены необходимые учетные данные Instagram")
    
    def _make_request(self, method: str, url: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Выполнение запроса к API Instagram
        
        Args:
            method: HTTP метод (GET, POST)
            url: URL запроса
            params: Параметры запроса
            data: Данные для POST запроса
            
        Returns:
            Dict[str, Any]: Ответ от API
            
        Raises:
            requests.exceptions.RequestException: При ошибке запроса
        """
        params = params or {}
        params['access_token'] = self.access_token
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params)
            else:
                response = requests.post(url, json=data)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка API запроса: {str(e)}")
            if response is not None:
                logger.error(f"Ответ API: {response.text}")
            raise
    
    def get_account_info(self) -> Dict[str, Any]:
        """Получение информации об Instagram аккаунте"""
        url = f'https://graph.facebook.com/v21.0/{self.business_account_id}'
        params = {
            'fields': 'name,username,profile_picture_url'
        }
        return self._make_request('GET', url, params)
    
    def get_messages(self, limit: int = 10) -> Dict[str, Any]:
        """
        Получение сообщений из Instagram
        
        Args:
            limit: Максимальное количество сообщений
        """
        url = f'https://graph.facebook.com/v21.0/{self.business_account_id}/messages'
        params = {
            'fields': 'from,message,created_time',
            'limit': limit
        }
        return self._make_request('GET', url, params)
    
    def send_message(self, text: str, recipient_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Отправка сообщения
        
        Args:
            text: Текст сообщения
            recipient_id: ID получателя (если не указан, используется ID страницы)
        """
        url = f'https://graph.facebook.com/v21.0/{self.page_id}/messages'
        data = {
            'recipient': {'id': recipient_id or self.page_id},
            'message': {'text': text},
            'messaging_type': 'RESPONSE',
            'access_token': self.access_token
        }
        return self._make_request('POST', url, data=data)
    
    def verify_token(self) -> bool:
        """Проверка валидности токена"""
        try:
            url = 'https://graph.facebook.com/v21.0/me/accounts'
            params = {
                'fields': 'instagram_business_account,name'
            }
            data = self._make_request('GET', url, params)
            
            if 'data' in data:
                for page in data['data']:
                    if 'instagram_business_account' in page:
                        ig_account_id = page['instagram_business_account']['id']
                        logger.info(f"Найден Instagram Business Account ID: {ig_account_id}")
                        
                        # Сохраняем ID в базу
                        credentials_manager.set_credential(
                            'instagram',
                            'business_account_id',
                            ig_account_id,
                            'Instagram Business Account ID'
                        )
                        return True
            
            logger.warning("Instagram Business Account ID не найден")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при проверке токена: {str(e)}")
            return False

def main():
    """Основная функция скрипта"""
    parser = argparse.ArgumentParser(description='Управление Instagram интеграцией')
    parser.add_argument('action', choices=['info', 'messages', 'send', 'verify'],
                       help='Действие: info (информация об аккаунте), messages (получить сообщения), '
                            'send (отправить сообщение), verify (проверить токен)')
    parser.add_argument('--message', help='Текст сообщения для отправки')
    parser.add_argument('--recipient', help='ID получателя для отправки сообщения')
    parser.add_argument('--limit', type=int, default=10, help='Лимит сообщений для получения')
    
    args = parser.parse_args()
    
    try:
        setup_logger()
        manager = InstagramManager()
        
        if args.action == 'info':
            info = manager.get_account_info()
            print("\nИнформация об Instagram аккаунте:")
            print(f"Имя: {info.get('name', 'Н/Д')}")
            print(f"Username: {info.get('username', 'Н/Д')}")
            print(f"URL фото профиля: {info.get('profile_picture_url', 'Н/Д')}")
            
        elif args.action == 'messages':
            messages = manager.get_messages(args.limit)
            print(f"\nПоследние {args.limit} сообщений:")
            for msg in messages.get('data', []):
                created = datetime.fromisoformat(msg['created_time'].replace('Z', '+00:00'))
                print(f"\nОт: {msg.get('from', {}).get('name', 'Н/Д')}")
                print(f"Время: {created.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Сообщение: {msg.get('message', 'Н/Д')}")
            
        elif args.action == 'send':
            if not args.message:
                parser.error("Для отправки сообщения требуется параметр --message")
            
            result = manager.send_message(args.message, args.recipient)
            if 'message_id' in result:
                print("\n✅ Сообщение успешно отправлено!")
            else:
                print("\n❌ Ошибка при отправке сообщения")
            
        elif args.action == 'verify':
            if manager.verify_token():
                print("\n✅ Токен валиден, ID бизнес-аккаунта сохранен")
            else:
                print("\n❌ Ошибка проверки токена")
    
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
