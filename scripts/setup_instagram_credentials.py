#!/usr/bin/env python3

import os
import sys
import argparse

# Добавляем путь к корневой директории проекта
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
os.environ['PYTHONPATH'] = project_root

from src.utils.credentials_manager import credentials_manager

def setup_instagram_credentials(access_token: str, page_id: str):
    """
    Настройка учетных данных Instagram
    
    Args:
        access_token: Instagram Graph API Access Token
        page_id: Facebook Page ID
    """
    credentials = [
        {
            'service_name': 'instagram',
            'credential_key': 'access_token',
            'credential_value': access_token,
            'description': 'Instagram Graph API Access Token'
        },
        {
            'service_name': 'instagram',
            'credential_key': 'page_id',
            'credential_value': page_id,
            'description': 'Facebook Page ID'
        }
    ]
    
    for cred in credentials:
        query = """
        INSERT INTO credentials (service_name, credential_key, credential_value, description)
        VALUES (%(service_name)s, %(credential_key)s, %(credential_value)s, %(description)s)
        ON CONFLICT (service_name, credential_key) 
        DO UPDATE SET 
            credential_value = EXCLUDED.credential_value,
            description = EXCLUDED.description;
        """
        
        credentials_manager.execute_query(query, cred)
        print(f"✅ Сохранено: {cred['service_name']}.{cred['credential_key']}")

def main():
    parser = argparse.ArgumentParser(description='Настройка учетных данных Instagram')
    parser.add_argument('--access-token', required=True, help='Instagram Graph API Access Token')
    parser.add_argument('--page-id', required=True, help='Facebook Page ID')
    
    args = parser.parse_args()
    setup_instagram_credentials(args.access_token, args.page_id)

if __name__ == '__main__':
    main()
