#!/usr/bin/env python3
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
import psycopg2
from psycopg2.extras import DictCursor

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_service_account():
    """Получаем service account из базы данных"""
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute(
        """
        SELECT credential_value 
        FROM credentials 
        WHERE service_name = 'google' AND credential_key = 'service_account'
        """
    )
    return json.loads(cur.fetchone()['credential_value'])

def check_cloud_run():
    """Проверяем сервисы в Cloud Run"""
    try:
        # Получаем service account
        service_account_info = get_service_account()
        
        # Создаем credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Создаем сервис
        service = build('run', 'v1', credentials=credentials)
        
        # Получаем список сервисов
        project_id = service_account_info['project_id']
        parent = f'projects/{project_id}/locations/-'
        
        request = service.projects().locations().services().list(parent=parent)
        response = request.execute()
        
        if 'items' in response:
            logger.info("\nНайдены сервисы в Cloud Run:")
            for service in response['items']:
                logger.info(f"\nИмя сервиса: {service['name']}")
                logger.info(f"URL: {service.get('status', {}).get('url')}")
                logger.info(f"Состояние: {service.get('status', {}).get('conditions', [{}])[0].get('message')}")
        else:
            logger.info("Сервисы не найдены")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке Cloud Run: {str(e)}")

if __name__ == '__main__':
    check_cloud_run()
