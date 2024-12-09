import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.services.sheets_service import SheetsService
from src.config.config import Config

async def init_catalog():
    """Initialize the catalog sheet and add some test data."""
    try:
        sheets_service = SheetsService()
        
        # Initialize the catalog sheet
        await sheets_service.initialize_catalog_sheet()
        
        # Add some test items
        test_items = [
            {
                'name': 'Красные розы',
                'quantity': 50,
                'price': 1500,
                'description': 'Свежие красные розы, длина стебля 60 см',
                'category': 'Розы'
            },
            {
                'name': 'Белые хризантемы',
                'quantity': 30,
                'price': 800,
                'description': 'Белые хризантемы, крупный бутон',
                'category': 'Хризантемы'
            },
            {
                'name': 'Тюльпаны микс',
                'quantity': 100,
                'price': 500,
                'description': 'Тюльпаны разных цветов',
                'category': 'Тюльпаны'
            }
        ]
        
        for item in test_items:
            await sheets_service.add_inventory_item(item)
            print(f"Added item: {item['name']}")
        
        print("Catalog initialization completed successfully!")
        
    except Exception as e:
        print(f"Error initializing catalog: {e}")

if __name__ == "__main__":
    asyncio.run(init_catalog())
