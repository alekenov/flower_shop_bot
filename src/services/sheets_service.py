import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from ..config.config import Config

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.config = Config()
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self._setup_service()

    def _setup_service(self):
        """Инициализация сервиса Google Sheets"""
        try:
            credentials = Credentials.from_service_account_file(
                self.config.GOOGLE_SHEETS_CREDENTIALS_FILE, 
                scopes=self.SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            self.spreadsheet_id = self.config.GOOGLE_SHEETS_SPREADSHEET_ID
        except Exception as e:
            logger.error(f"Error setting up Google Sheets service: {e}")
            raise

    def log_conversation(self, user_id: int, user_message: str, bot_response: str):
        """
        Логирование диалога в Google Sheets
        """
        try:
            # Подготовка данных для записи
            values = [[
                str(user_id),
                user_message,
                bot_response,
                "=NOW()"  # Текущее время
            ]]

            body = {
                'values': values
            }

            # Запись в таблицу
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Conversations!A:D',  # Диапазон для записи
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

        except Exception as e:
            logger.error(f"Error logging to Google Sheets: {e}")
            # Не прерываем работу бота при ошибке логирования
            pass
