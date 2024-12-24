import os
import json
import logging
import time
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from services.config_service import config_service
from utils.logger_config import get_logger
from typing import List, Optional
import datetime
import asyncio
import json
from services.config_service import ConfigService
from services.postgres_service import PostgresService

# Setup logging
logger = get_logger('sheets_service', logging.DEBUG)

class SheetsService:
    def __init__(self):
        self.config = ConfigService()
        self.db = PostgresService()
        self.credentials = None
        self.service = None
        self.spreadsheet_id = None
        self.update_interval = None

    async def initialize(self):
        """Асинхронная инициализация"""
        if not self.credentials:  # Проверяем, не инициализированы ли мы уже
            await self._setup()

    async def _setup(self):
        """Инициализация сервиса"""
        self.credentials = await self.config.get_google_credentials()
        self.service = build('sheets', 'v4', credentials=self.credentials)
        self.spreadsheet_id = await self.config.get_config_async('spreadsheet_id', 'google')
        self.update_interval = int(await self.config.get_config_async('update_interval', 'cache'))

    async def _get_cached_data(self, source: str) -> Optional[dict]:
        """Получение данных из кэша"""
        await self.db.connect()  # Убедимся что подключены к базе
        return await self.db.get_from_cache(source, self.update_interval)

    async def _update_cache(self, source: str, data: dict):
        """Обновление кэша"""
        await self.db.connect()  # Убедимся что подключены к базе
        await self.db.save_to_cache(source, data)

    async def update_data(self) -> bool:
        """Принудительное обновление данных"""
        try:
            # Получаем свежие данные
            sheet_data = await self._fetch_sheet_data()
            
            # Обновляем кэш
            await self._update_cache('google_sheets', sheet_data)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении данных: {e}")
            return False

    async def get_data(self) -> dict:
        """Получение данных с учетом кэша"""
        # Пробуем получить из кэша
        cached_data = await self._get_cached_data('google_sheets')
        if cached_data:
            return cached_data
            
        # Если нет в кэше - получаем и кэшируем
        data = await self._fetch_sheet_data()
        await self._update_cache('google_sheets', data)
        return data

    async def _fetch_sheet_data(self):
        """Получение данных из таблицы"""
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range='Sheet1!A2:E'
        ).execute()
        
        values = result.get('values', [])
        data = []
        for row in values:
            if len(row) >= 2:
                name = row[0].strip()
                price = row[1].strip()
                if name and price:
                    try:
                        # Пытаемся преобразовать цену в число для форматирования
                        price_num = float(price.replace(' ', '').replace('тг', '').replace('тенге', ''))
                        formatted_price = f"{price_num:,.0f} тг".replace(',', ' ')
                        data.append({
                            'name': name,
                            'price': formatted_price,
                            'quantity': int(row[2]) if len(row) > 2 and row[2].strip().isdigit() else 0,
                            'description': row[3].strip() if len(row) > 3 else '',
                            'category': row[4].strip() if len(row) > 4 else ''
                        })
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid price format for {name}: {price}")
                        continue
        
        return data

    def _verify_access(self):
        """Verify access to the spreadsheet."""
        try:
            self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
        except Exception as e:
            logger.error(f"Failed to verify access to spreadsheet: {str(e)}")
            raise

    def _get_sheet_names(self):
        """Get all sheet names from the spreadsheet."""
        try:
            sheets = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            return [sheet['properties']['title'] for sheet in sheets['sheets']]
        except Exception as e:
            logger.error(f"Failed to get sheet names: {str(e)}")
            return []

    async def get_inventory_data(self):
        """Get inventory data from Google Sheets."""
        try:
            # Пробуем получить данные из кэша
            cached_data = await self._get_cached_data('inventory')
            if cached_data:
                logger.info(f"Получены данные из кэша: {json.dumps(cached_data, ensure_ascii=False, indent=2)}")
                return cached_data

            logger.info("Данные в кэше не найдены, получаем из Google Sheets")
            
            # Если нет в кэше, получаем из таблицы
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Sheet1!A2:E'
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"Получены сырые данные из таблицы: {json.dumps(values, ensure_ascii=False, indent=2)}")
            
            inventory = []
            
            for row in values:
                if len(row) >= 2:  # Проверяем, что есть хотя бы название и цена
                    try:
                        name = row[0].strip()
                        price = row[1].strip()
                        quantity = int(row[2].strip()) if len(row) > 2 else 0
                        description = row[3].strip() if len(row) > 3 else ''
                        category = row[4].strip() if len(row) > 4 else ''
                        
                        item = {
                            'name': name,
                            'price': price,
                            'quantity': quantity,
                            'description': description,
                            'category': category
                        }
                        inventory.append(item)
                        logger.info(f"Обработан товар: {json.dumps(item, ensure_ascii=False)}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Ошибка обработки строки {row}: {str(e)}")
                        continue
                else:
                    logger.warning(f"Пропущена строка с недостаточным количеством данных: {row}")
            
            logger.info(f"Итоговый инвентарь: {json.dumps(inventory, ensure_ascii=False, indent=2)}")
            return inventory
            
        except Exception as e:
            logger.error(f"Ошибка получения данных инвентаря: {str(e)}", exc_info=True)
            return []

    async def format_inventory_for_openai(self, inventory):
        """Format inventory data for OpenAI prompt."""
        if not inventory:
            logger.warning("Получен пустой инвентарь для форматирования")
            return "Информация о товарах временно недоступна."

        logger.info("Начинаем форматирование инвентаря для OpenAI")
        formatted_text = "Текущий ассортимент:\n\n"

        # Группируем товары по категориям
        categories = {}
        for item in inventory:
            category = item.get('category', 'Разное')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        logger.info(f"Товары сгруппированы по категориям: {list(categories.keys())}")

        # Форматируем каждую категорию
        for category, items in categories.items():
            formatted_text += f" {category}:\n"
            for item in items:
                name = item.get('name', '')
                price = item.get('price', '')
                quantity = item.get('quantity', 0)
                description = item.get('description', '')

                item_text = f"- {name}: {price}"
                if quantity > 0:
                    item_text += f" (в наличии: {quantity})"
                if description:
                    item_text += f"\n  {description}"
                formatted_text += item_text + "\n"
            formatted_text += "\n"
        
        logger.info(f"Отформатированный текст для OpenAI:\n{formatted_text}")
        return formatted_text

    async def update_inventory_item(self, item_name: str, updates: dict):
        """Update inventory item data in Google Sheets."""
        try:
            logger.info(f"Updating inventory item: {item_name}")
            
            # Validate updates
            is_valid, error_msg = self._validate_item_data({'name': item_name, **updates})
            if not is_valid:
                logger.error(f"Invalid update data for {item_name}: {error_msg}")
                return False
            
            # Get current inventory
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Sheet1!A2:E'
            ).execute()
            
            values = result.get('values', [])
            row_index = None
            
            # Find the row and check if update is needed
            for i, row in enumerate(values, start=2):
                if row[0] == item_name:
                    row_index = i
                    current_row = row
                    break
            
            if row_index is None:
                logger.error(f"Item {item_name} not found in inventory")
                return False
            
            # Prepare the update
            new_row = current_row.copy()
            
            # Update fields based on the updates dictionary
            if 'quantity' in updates:
                new_row[1] = str(updates['quantity'])
            if 'price' in updates:
                new_row[2] = str(updates['price'])
            if 'description' in updates:
                new_row[3] = updates['description']
            if 'category' in updates:
                new_row[4] = updates['category']
            
            # Check if the data actually changed
            if self._get_row_hash(current_row) == self._get_row_hash(new_row):
                logger.info(f"No changes detected for item: {item_name}")
                return True
            
            # Store the previous version
            version_sheet = self._get_version_sheet_name()
            self._ensure_version_sheet_exists(version_sheet)
            
            timestamp = datetime.datetime.now().isoformat()
            version_row = [timestamp, item_name] + current_row[1:]
            
            # Append to version history
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{version_sheet}!A:F',
                valueInputOption='RAW',
                body={'values': [version_row]}
            ).execute()
            
            # Update the main sheet
            range_name = f'Sheet1!A{row_index}:E{row_index}'
            body = {
                'values': [new_row]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"Successfully updated inventory item: {item_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update inventory item: {str(e)}", exc_info=True)
            return False

    def _validate_item_data(self, item_data: dict) -> tuple[bool, str]:
        """Validate item data before updating or adding to sheets.
        
        Args:
            item_data (dict): Dictionary containing item data to validate
            
        Returns:
            tuple[bool, str]: (is_valid, error_message)
        """
        try:
            required_fields = ['name']
            for field in required_fields:
                if field not in item_data or not item_data[field]:
                    return False, f"Missing required field: {field}"
            
            if 'quantity' in item_data:
                try:
                    quantity = int(item_data['quantity'])
                    if quantity < 0:
                        return False, "Quantity cannot be negative"
                except ValueError:
                    return False, "Quantity must be a valid number"
            
            if 'price' in item_data:
                try:
                    price = float(str(item_data['price']).replace(' тенге', ''))
                    if price < 0:
                        return False, "Price cannot be negative"
                except ValueError:
                    return False, "Price must be a valid number"
            
            return True, ""
        except Exception as e:
            logger.error(f"Error validating item data: {str(e)}", exc_info=True)
            return False, f"Validation error: {str(e)}"

    def _get_row_hash(self, row: list) -> str:
        """Generate a hash for a row to detect changes.
        
        Args:
            row (list): Row data to hash
            
        Returns:
            str: Hash of the row data
        """
        import hashlib
        row_str = '|'.join(str(cell) for cell in row)
        return hashlib.md5(row_str.encode()).hexdigest()

    def _get_version_sheet_name(self) -> str:
        """Get the name of the version tracking sheet."""
        from datetime import datetime
        current_date = datetime.now().strftime('%Y_%m')
        return f'Version_{current_date}'

    def _ensure_version_sheet_exists(self, sheet_name: str):
        """Ensure version tracking sheet exists with correct headers."""
        try:
            sheets = self._get_sheet_names()
            if sheet_name not in sheets:
                # Create new sheet
                request = {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }
                
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': [request]}
                ).execute()
                
                # Add headers
                headers = [['Timestamp', 'Item Name', 'Quantity', 'Price', 'Description', 'Category']]
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A1:F1',
                    valueInputOption='RAW',
                    body={'values': headers}
                ).execute()
                
                logger.info(f"Created new version sheet: {sheet_name}")
                
        except Exception as e:
            logger.error(f"Error ensuring version sheet exists: {str(e)}", exc_info=True)
            raise

    async def add_inventory_item(self, item_data: dict):
        """Add a new item to the inventory.
        
        Args:
            item_data (dict): Dictionary containing item data
                (name, quantity, price, description, category)
        """
        try:
            logger.info(f"Adding new inventory item: {item_data.get('name')}")
            
            # Validate item data
            is_valid, error_msg = self._validate_item_data(item_data)
            if not is_valid:
                logger.error(f"Invalid item data: {error_msg}")
                return False
            
            # Prepare the new row
            new_row = [
                item_data.get('name', ''),
                str(item_data.get('quantity', 0)),
                str(item_data.get('price', 0)),
                item_data.get('description', ''),
                item_data.get('category', '')
            ]
            
            # Append to the sheet
            body = {
                'values': [new_row]
            }
            
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Sheet1!A2:E',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Successfully added new inventory item: {item_data.get('name')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add inventory item: {str(e)}", exc_info=True)
            return False
    
    async def get_inventory_item(self, item_name: str):
        """Get details of a specific inventory item.
        
        Args:
            item_name (str): Name of the item to retrieve
        """
        try:
            logger.info(f"Getting inventory item: {item_name}")
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Sheet1!A2:E'
            ).execute()
            
            values = result.get('values', [])
            
            for i, row in enumerate(values, start=2):  
                if row[0] == item_name:
                    return {
                        'name': row[0],
                        'quantity': int(row[1]) if row[1].isdigit() else 0,
                        'price': str(float(row[2])) + " тенге" if row[2].replace('.', '').isdigit() else "0 тенге",
                        'description': row[3] if len(row) > 3 else '',
                        'category': row[4] if len(row) > 4 else ''
                    }
            
            logger.error(f"Item {item_name} not found in inventory")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get inventory item: {str(e)}", exc_info=True)
            return None

    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get the sheet ID for a given sheet name."""
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        raise ValueError(f"Sheet {sheet_name} not found")

    async def initialize_catalog_sheet(self):
        """Initialize or update the Catalog sheet with the correct structure."""
        try:
            logger.info("Initializing Catalog sheet")
            
            # Check if Catalog sheet exists
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            catalog_exists = any(sheet['properties']['title'] == 'Sheet1' for sheet in sheets)
            
            if not catalog_exists:
                # Create new sheet
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': 'Sheet1'
                        }
                    }
                }]
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                logger.info("Created new Catalog sheet")
            
            # Set up headers
            headers = [
                ['Название', 'Количество', 'Цена', 'Описание', 'Категория']
            ]
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range='Sheet1!A1:E1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            
            # Format headers (make bold and freeze)
            requests = [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': self._get_sheet_id('Sheet1'),
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 5
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {'bold': True},
                                'backgroundColor': {
                                    'red': 0.9,
                                    'green': 0.9,
                                    'blue': 0.9
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                },
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': self._get_sheet_id('Sheet1'),
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }
            ]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
            logger.info("Successfully initialized Catalog sheet")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Catalog sheet: {str(e)}", exc_info=True)
            return False

    async def get_specific_flowers(self, flower_types: List[str]) -> Optional[str]:
        """Get information about specific flowers."""
        try:
            if not flower_types:
                return None

            # Получаем данные из кэша
            values = await self.get_data()
            if not values:
                logger.warning("No data found in spreadsheet")
                return None

            # Если запрошены все цветы
            if 'все' in flower_types:
                result = []
                for row in values:
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        result.append(f"{row[0].strip()} - {row[1].strip()} тг")
                return "\n".join(result) if result else None

            # Если запрошены конкретные цветы
            result = []
            for row in values:
                if len(row) >= 2 and row[0].strip() and row[1].strip():
                    name = row[0].strip().lower()
                    if any(flower.lower() in name for flower in flower_types):
                        result.append(f"{row[0].strip()} - {row[1].strip()} тг")
            
            return "\n".join(result) if result else None

        except Exception as e:
            logger.error(f"Error getting specific flowers: {e}")
            return None
