import os
import json
import logging
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from services.config_service import config_service

logger = logging.getLogger(__name__)

class SheetsService:
    def __init__(self):
        """Initialize the Google Sheets service."""
        try:
            self.spreadsheet_id = config_service.get_config('GOOGLE_SHEETS_SPREADSHEET_ID')
            if not self.spreadsheet_id:
                raise ValueError("Google Sheets spreadsheet ID not found in config")
            
            logger.info(f"Initializing Google Sheets service with spreadsheet ID: {self.spreadsheet_id}")
            
            # Load credentials from service account JSON
            service_account_info = json.loads(config_service.get_config('GOOGLE_SERVICE_ACCOUNT'))
            if not service_account_info:
                raise ValueError("Google service account credentials not found in config")
                
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            logger.info("Successfully loaded credentials")
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            logger.info("Successfully built Google Sheets service")
            
            # Verify access and get sheet names
            self._verify_access()
            logger.info("Successfully verified access to spreadsheet")
            
            sheet_names = self._get_sheet_names()
            logger.info(f"Available sheets: {sheet_names}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}", exc_info=True)
            raise

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
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            return [sheet['properties']['title'] for sheet in result['sheets']]
        except Exception as e:
            logger.error(f"Failed to get sheet names: {str(e)}")
            return []

    def get_inventory_data(self):
        """Get inventory data from Google Sheets."""
        try:
            possible_ranges = ['Catalog!A2:E', 'Sheet1!A2:E', 'Лист1!A2:E', 'Каталог!A2:E']
            values = []
            
            for sheet_range in possible_ranges:
                try:
                    logger.info(f"Trying to read from range: {sheet_range}")
                    result = self.service.spreadsheets().values().get(
                        spreadsheetId=self.spreadsheet_id,
                        range=sheet_range
                    ).execute()
                    values = result.get('values', [])
                    if values:
                        logger.info(f"Successfully read data from {sheet_range}")
                        break
                except Exception as e:
                    logger.warning(f"Could not read from {sheet_range}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(values)} rows from spreadsheet")
            
            if not values:
                logger.warning("No data found in spreadsheet")
                return []
            
            inventory = []
            for i, row in enumerate(values, start=2):
                try:
                    # Убедимся, что у нас есть все необходимые колонки
                    while len(row) < 4:
                        row.append('')  # Добавляем пустые значения если не хватает колонок
                    
                    # Очищаем и проверяем значения
                    name = row[0].strip() if row[0] else ''
                    price = row[1].strip() if len(row) > 1 else ''
                    quantity = row[2].strip() if len(row) > 2 else ''
                    description = row[3].strip() if len(row) > 3 else ''
                    
                    # Проверяем обязательные поля
                    if not name:
                        logger.warning(f"Пропускаем строку {i}: отсутствует название")
                        continue
                    
                    # Преобразуем price в число
                    try:
                        price_clean = ''.join(c for c in price if c.isdigit() or c == '.')
                        if price_clean:
                            price_value = float(price_clean)
                            if price_value <= 0:
                                logger.warning(f"Пропускаем строку {i}: некорректная цена {price}")
                                continue
                            price = f"{int(price_value)} тенге"
                        else:
                            logger.warning(f"Пропускаем строку {i}: отсутствует цена")
                            continue
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Пропускаем строку {i}: ошибка при обработке цены {price}: {e}")
                        continue
                    
                    # Преобразуем quantity в число
                    try:
                        quantity = int(quantity) if quantity.isdigit() else 0
                        if quantity < 0:
                            logger.warning(f"Корректируем отрицательное количество в строке {i}")
                            quantity = 0
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Ошибка при обработке количества в строке {i}: {e}")
                        quantity = 0
                    
                    item = {
                        'name': name,
                        'price': price,
                        'quantity': quantity,
                        'description': description
                    }
                    
                    logger.info(f"Обработана строка {i}: {item}")
                    inventory.append(item)
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке строки {i}: {e}", exc_info=True)
                    logger.error(f"Проблемная строка: {row}")
                    continue
            
            logger.info(f"Успешно обработано {len(inventory)} товаров")
            return inventory
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных: {str(e)}", exc_info=True)
            return []

    def format_inventory_for_openai(self, inventory):
        """Format inventory data for OpenAI prompt."""
        if not inventory:
            return "В данный момент информация о наличии цветов недоступна."
        
        # Форматируем каждый товар
        items = []
        for item in inventory:
            name = item.get('name', '').strip()
            price = item.get('price', '0 тенге').strip()
            quantity = item.get('quantity', 0)
            description = item.get('description', '').strip()
            
            # Добавляем информацию о наличии
            availability = "в наличии" if quantity > 0 else "нет в наличии"
            
            # Формируем строку с описанием товара
            item_str = f"- {name} ({price})"
            if description:
                item_str += f" - {description}"
            
            items.append(item_str)
        
        return "\n".join(items)

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
                range='Catalog!A2:E'
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
            
            timestamp = datetime.now().isoformat()
            version_row = [timestamp, item_name] + current_row[1:]
            
            # Append to version history
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{version_sheet}!A:F',
                valueInputOption='RAW',
                body={'values': [version_row]}
            ).execute()
            
            # Update the main sheet
            range_name = f'Catalog!A{row_index}:E{row_index}'
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
                range='Catalog!A2:E',
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
                range='Catalog!A2:E'
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

    async def initialize_catalog_sheet(self):
        """Initialize or update the Catalog sheet with the correct structure."""
        try:
            logger.info("Initializing Catalog sheet")
            
            # Check if Catalog sheet exists
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            catalog_exists = any(sheet['properties']['title'] == 'Catalog' for sheet in sheets)
            
            if not catalog_exists:
                # Create new sheet
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': 'Catalog'
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
                range='Catalog!A1:E1',
                valueInputOption='RAW',
                body={'values': headers}
            ).execute()
            
            # Format headers (make bold and freeze)
            requests = [
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': self._get_sheet_id('Catalog'),
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
                            'sheetId': self._get_sheet_id('Catalog'),
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
    
    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get the sheet ID for a given sheet name."""
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        for sheet in spreadsheet.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        raise ValueError(f"Sheet {sheet_name} not found")
