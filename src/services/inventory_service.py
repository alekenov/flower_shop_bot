from typing import List, Dict, Optional
from google_service import GoogleService
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InventoryService:
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.google_service = GoogleService("flower_shop_bot_service_account")
        self.range_name = 'A:D'  # Диапазон для всех колонок
        
    async def get_all_products(self) -> List[Dict]:
        """Получение всех товаров из инвентаря"""
        try:
            result = await self.google_service.get_spreadsheet_values(
                self.spreadsheet_id,
                self.range_name
            )
            
            values = result.get('values', [])
            if not values:
                return []
            
            # Пропускаем заголовок и преобразуем в список словарей
            products = []
            headers = ["name", "price", "quantity", "description"]
            
            for row in values[1:]:  # Пропускаем заголовок
                product = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        product[headers[i]] = value
                products.append(product)
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting products: {str(e)}")
            raise

    async def get_product_by_name(self, name: str) -> Optional[Dict]:
        """Поиск товара по названию"""
        try:
            products = await self.get_all_products()
            for product in products:
                if product['name'].lower() == name.lower():
                    return product
            return None
        except Exception as e:
            logger.error(f"Error finding product: {str(e)}")
            raise

    async def update_quantity(self, name: str, new_quantity: int) -> bool:
        """Обновление количества товара"""
        try:
            # Получаем все значения
            result = await self.google_service.get_spreadsheet_values(
                self.spreadsheet_id,
                self.range_name
            )
            
            values = result.get('values', [])
            if not values:
                return False
            
            # Ищем строку с нужным товаром
            row_index = None
            for i, row in enumerate(values):
                if i > 0 and row[0].lower() == name.lower():  # Пропускаем заголовок
                    row_index = i
                    break
            
            if row_index is None:
                return False
            
            # Обновляем количество
            range_name = f'C{row_index + 1}'  # +1 потому что в Google Sheets строки начинаются с 1
            await self.google_service.update_spreadsheet_values(
                self.spreadsheet_id,
                range_name,
                'RAW',
                [[str(new_quantity)]]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating quantity: {str(e)}")
            raise

    async def add_product(self, name: str, price: str, quantity: str, description: str) -> bool:
        """Добавление нового товара"""
        try:
            # Получаем текущие значения, чтобы определить следующую строку
            result = await self.google_service.get_spreadsheet_values(
                self.spreadsheet_id,
                self.range_name
            )
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Добавляем новый товар
            range_name = f'A{next_row}:D{next_row}'
            await self.google_service.update_spreadsheet_values(
                self.spreadsheet_id,
                range_name,
                'RAW',
                [[name, price, quantity, description]]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding product: {str(e)}")
            raise

    async def check_availability(self, name: str, required_quantity: int) -> bool:
        """Проверка доступности товара в нужном количестве"""
        try:
            product = await self.get_product_by_name(name)
            if not product:
                return False
            
            available_quantity = int(product['quantity'])
            return available_quantity >= required_quantity
            
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            raise

# Создаем экземпляр сервиса с ID нашей таблицы
inventory_service = InventoryService("1Cqk6yXfblRvTN0m_BmJVqn9zf4AQZZdQeyFcjPlM1jk")
