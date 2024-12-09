import os
import logging
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config.config import Config
from datetime import datetime

logger = logging.getLogger(__name__)

class SheetsService:
    def __init__(self):
        """Initialize the Google Sheets service."""
        try:
            config = Config()
            self.spreadsheet_id = config.GOOGLE_SHEETS_SPREADSHEET_ID
            self.credentials_file = config.GOOGLE_SHEETS_CREDENTIALS_FILE
            
            logger.info(f"Initializing Google Sheets service with:")
            logger.info(f"- Spreadsheet ID: {self.spreadsheet_id}")
            logger.info(f"- Credentials file: {self.credentials_file}")
            
            # Load credentials
            self.credentials = self._load_credentials()
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

    def _load_credentials(self):
        """Load Google Sheets credentials from the credentials file."""
        try:
            logger.info(f"Loading credentials from file: {self.credentials_file}")
            return service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets']  # Full access to sheets
            )
        except Exception as e:
            logger.error(f"Failed to load credentials: {str(e)}", exc_info=True)
            raise
    
    def _verify_access(self):
        """Verify access to the spreadsheet."""
        try:
            result = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            logger.info(f"Successfully accessed spreadsheet: {result.get('properties', {}).get('title')}")
        except Exception as e:
            logger.error(f"Failed to verify access to spreadsheet: {str(e)}", exc_info=True)
            raise

    def _get_sheet_names(self):
        """Get all sheet names from the spreadsheet."""
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]
            return sheet_names
        except Exception as e:
            logger.error(f"Failed to get sheet names: {str(e)}", exc_info=True)
            raise

    async def get_inventory_data(self):
        """Get inventory data from Google Sheets."""
        try:
            logger.info(f"Getting inventory data from spreadsheet {self.spreadsheet_id}")
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Catalog!A2:E'
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"Retrieved {len(values)} rows from spreadsheet")
            
            if not values:
                logger.warning("No data found in spreadsheet")
                return []
            
            inventory = []
            for i, row in enumerate(values, start=2):
                try:
                    if len(row) >= 3:
                        item = {
                            'name': row[0],
                            'quantity': int(row[1]) if row[1].isdigit() else 0,
                            'price': str(float(row[2])) + " тенге" if row[2].replace('.', '').isdigit() else "0 тенге",
                            'description': row[3] if len(row) > 3 else '',
                            'category': row[4] if len(row) > 4 else ''
                        }
                        inventory.append(item)
                        logger.debug(f"Processed row {i}: {item}")
                except Exception as e:
                    logger.error(f"Error processing row {i} ({row}): {str(e)}", exc_info=True)
                    continue
            
            logger.info(f"Successfully processed {len(inventory)} inventory items")
            return inventory
            
        except Exception as e:
            logger.error(f"Failed to get inventory data: {str(e)}", exc_info=True)
            raise

    def format_inventory_for_openai(self, inventory):
        """Format inventory data for OpenAI prompt."""
        if not inventory:
            return "В данный момент информация о товарах недоступна."
        
        formatted_info = "Актуальная информация о товарах:\n\n"
        for item in inventory:
            formatted_info += f"- {item['name']}:\n"
            formatted_info += f"  Количество: {item['quantity']} шт.\n"
            formatted_info += f"  Цена: {item['price']}\n"
            if 'description' in item:
                formatted_info += f"  Описание: {item['description']}\n"
            formatted_info += "\n"
        
        return formatted_info

    async def update_inventory_item(self, item_name: str, updates: dict):
        """Update inventory item data in Google Sheets.
        
        Args:
            item_name (str): Name of the item to update
            updates (dict): Dictionary containing updates (quantity, price, etc.)
        """
        try:
            logger.info(f"Updating inventory item: {item_name}")
            
            # First, get the current inventory to find the row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Catalog!A2:E'
            ).execute()
            
            values = result.get('values', [])
            row_index = None
            
            # Find the row with the matching item name
            for i, row in enumerate(values, start=2):  
                if row[0] == item_name:
                    row_index = i
                    break
            
            if row_index is None:
                logger.error(f"Item {item_name} not found in inventory")
                return False
            
            # Prepare the update
            current_row = values[row_index-2]  
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
            
            # Update the sheet
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
    
    async def add_inventory_item(self, item_data: dict):
        """Add a new item to the inventory.
        
        Args:
            item_data (dict): Dictionary containing item data
                (name, quantity, price, description, category)
        """
        try:
            logger.info(f"Adding new inventory item: {item_data.get('name')}")
            
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
