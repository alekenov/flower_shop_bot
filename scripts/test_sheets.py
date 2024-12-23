import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import psycopg2
from psycopg2.extras import DictCursor

def get_sheets_data():
    # Подключаемся к базе данных
    conn = psycopg2.connect(
        "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )
    
    with conn.cursor(cursor_factory=DictCursor) as cur:
        # Получаем service account credentials
        cur.execute(
            """
            SELECT credential_value
            FROM credentials
            WHERE service_name = 'google' AND credential_key = 'service_account'
            """
        )
        service_account_info = json.loads(cur.fetchone()['credential_value'])
        
        # Получаем spreadsheet_id
        cur.execute(
            """
            SELECT credential_value
            FROM credentials
            WHERE service_name = 'google' AND credential_key = 'sheets_spreadsheet_id'
            """
        )
        spreadsheet_id = cur.fetchone()['credential_value']
    
    # Создаем credentials
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
    )
    
    # Создаем сервис
    service = build('sheets', 'v4', credentials=credentials)
    
    # Получаем список листов
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    print("Доступные листы:", [sheet['properties']['title'] for sheet in spreadsheet['sheets']])
    
    # Пробуем прочитать данные из разных диапазонов
    ranges = ['Sheet1!A2:E', 'Лист1!A2:E', 'Каталог!A2:E']
    for range_name in ranges:
        try:
            print(f"\nПробуем прочитать диапазон: {range_name}")
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            values = result.get('values', [])
            if values:
                print(f"Найдены данные в {range_name}:")
                for row in values:
                    print(row)
            else:
                print(f"Нет данных в {range_name}")
        except Exception as e:
            print(f"Ошибка при чтении {range_name}: {e}")

if __name__ == '__main__':
    get_sheets_data()
