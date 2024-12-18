from typing import List, Dict, Optional
import logging
from .supabase_service import SupabaseService

logger = logging.getLogger(__name__)

class ProductService:
    def __init__(self):
        self.db = SupabaseService()

    def get_all_products(self) -> List[Dict]:
        """Получить все доступные продукты."""
        try:
            return self.db.get_products()
        except Exception as e:
            logger.error(f"Error getting all products: {str(e)}")
            return []

    def get_product_by_name(self, name: str) -> Optional[Dict]:
        """Получить продукт по названию."""
        try:
            products = self.db.get_products()
            for product in products:
                if product['name'].lower() == name.lower():
                    return product
            return None
        except Exception as e:
            logger.error(f"Error getting product by name: {str(e)}")
            return None

    def get_products_by_category(self, category: str) -> List[Dict]:
        """Получить все продукты в указанной категории."""
        try:
            return self.db.get_products(category=category)
        except Exception as e:
            logger.error(f"Error getting products by category: {str(e)}")
            return []

    def check_availability(self, product_name: str, quantity: int) -> Dict:
        """Проверить наличие продукта в указанном количестве."""
        try:
            product = self.get_product_by_name(product_name)
            if not product:
                return {
                    "available": False,
                    "product_name": product_name,
                    "requested_quantity": quantity,
                    "available_quantity": 0,
                    "error": "Product not found"
                }

            return {
                "available": product['quantity'] >= quantity,
                "product_name": product_name,
                "requested_quantity": quantity,
                "available_quantity": product['quantity']
            }
        except Exception as e:
            logger.error(f"Error checking product availability: {str(e)}")
            return {
                "available": False,
                "product_name": product_name,
                "requested_quantity": quantity,
                "available_quantity": 0,
                "error": str(e)
            }

    def update_product_quantity(self, product_name: str, quantity_change: int) -> bool:
        """Обновить количество продукта (положительное значение для добавления, отрицательное для вычитания)."""
        try:
            return self.db.update_product_quantity(product_name, quantity_change)
        except Exception as e:
            logger.error(f"Error updating product quantity: {str(e)}")
            return False

# Создаем глобальный экземпляр сервиса
product_service = ProductService()
