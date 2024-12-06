import os
import logging
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config.config import Config

logger = logging.getLogger(__name__)

class SheetsService:
    def __init__(self):
        """Initialize the Google Sheets service."""
        try:
            config = Config()
            self.spreadsheet_id = config.GOOGLE_SHEETS_SPREADSHEET_ID
            self.credentials_file = config.GOOGLE_SHEETS_CREDENTIALS_FILE
            
            logger.info(f"Initializing Google Sheets service with spreadsheet ID: {self.spreadsheet_id}")
            logger.info(f"Using credentials from: {self.credentials_file}")
            
            # Load credentials
            self.credentials = self._load_credentials()
            logger.info("Successfully loaded credentials")
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            logger.info("Successfully built Google Sheets service")
            
            # Verify access and get sheet names
            self._verify_access()
            self._get_sheet_names()
            logger.info("Successfully verified access to spreadsheet")
            
            logger.info("Successfully initialized Google Sheets service")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            raise
    
    def _load_credentials(self):
        """Load Google Sheets credentials from the credentials file."""
        try:
            return service_account.Credentials.from_service_account_file(
                self.credentials_file,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise
    
    def _verify_access(self):
        """Verify access to the spreadsheet."""
        try:
            self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        except Exception as e:
            logger.error(f"Failed to verify access to spreadsheet: {e}")
            raise

    def _get_sheet_names(self):
        """Get all sheet names from the spreadsheet."""
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet['properties']['title'] for sheet in sheets]
            logger.info(f"Available sheets: {sheet_names}")
        except Exception as e:
            logger.error(f"Failed to get sheet names: {e}")
            raise

    async def get_inventory_data(self):
        """Get inventory data from Google Sheets."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='Catalog!A2:D'  # Changed from Inventory to Catalog
            ).execute()
            
            values = result.get('values', [])
            if not values:
                logger.warning("No data found in spreadsheet")
                return []
            
            inventory = []
            for row in values:
                if len(row) >= 3:  # Ensure we have at least name, quantity, and price
                    item = {
                        'name': row[0],
                        'quantity': int(row[1]) if row[1].isdigit() else 0,
                        'price': str(float(row[2])) + " тенге" if row[2].replace('.', '').isdigit() else "0 тенге"  
                    }
                    if len(row) >= 4:  # If description exists
                        item['description'] = row[3]
                    inventory.append(item)
            
            return inventory
            
        except Exception as e:
            logger.error(f"Failed to get inventory data: {e}")
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
