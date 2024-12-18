import os
import sys
import datetime
from dotenv import load_dotenv
import re
import json
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.services.sheets_service import SheetsService
from src.services.supabase_service import SupabaseService

def extract_price(price_str: str) -> float:
    """Извлекает числовое значение цены из строки."""
    # Находим все числа в строке (целые и десятичные)
    numbers = re.findall(r'\d+\.?\d*', price_str)
    if numbers:
        return float(numbers[0])
    return 0.0

def migrate_data():
    print("Starting migration from Google Sheets to Supabase...")
    
    try:
        # Инициализация сервисов
        sheets_service = SheetsService()
        supabase_service = SupabaseService()
        
        # Получение данных из Google Sheets
        print("Fetching data from Google Sheets...")
        inventory = sheets_service.get_inventory_data()
        print(f"Found {len(inventory)} products in Google Sheets")
        
        # Преобразование и загрузка данных в Supabase
        print("Uploading data to Supabase...")
        
        # Сначала очищаем все существующие продукты
        supabase_service.client.rpc('clear_products', {}).execute()
        print("Cleared existing products")
        
        # Небольшая пауза, чтобы дать время на обновление кэша
        time.sleep(1)
        
        # Затем добавляем новые продукты
        for item in inventory:
            try:
                name = item['name']
                quantity = int(float(str(item['quantity']).replace(',', '.')))
                price = extract_price(str(item['price']))
                description = item.get('description', '')
                
                # Добавляем продукт через RPC функцию
                supabase_service.client.rpc(
                    'add_product',
                    {
                        'p_name': name,
                        'p_price': price,
                        'p_quantity': quantity,
                        'p_description': description
                    }
                ).execute(params={})
                
                print(f"Processed: {name} - {price} тенге")
                
            except Exception as e:
                print(f"Error processing product {item['name']}: {str(e)}")
                if hasattr(e, 'json'):
                    print(f"Error details: {json.dumps(e.json(), indent=2)}")
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        if hasattr(e, 'json'):
            print(f"Error details: {json.dumps(e.json(), indent=2)}")
        raise

if __name__ == "__main__":
    load_dotenv()
    migrate_data()
