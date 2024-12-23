"""
Tests for all services (OpenAI, Sheets, Supabase, Instagram)
"""
import pytest
from unittest.mock import Mock, patch

from src.services.openai import OpenAIService
from src.services.sheets import SheetsService
from src.services.supabase import SupabaseService
from src.services.instagram import InstagramService

class TestOpenAIService:
    @pytest.fixture
    def openai_service(self):
        return OpenAIService()

    @patch('openai.AsyncOpenAI')
    async def test_generate_response(self, mock_openai, openai_service):
        """Test OpenAI response generation"""
        mock_openai.return_value.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Test response"))]
        )
        response = await openai_service.generate_response("Test prompt")
        assert response == "Test response"

class TestSheetsService:
    @pytest.fixture
    def sheets_service(self):
        return SheetsService()

    def test_read_sheet(self, sheets_service):
        """Test reading from Google Sheets"""
        with patch('src.services.sheets.build') as mock_build:
            mock_build.return_value.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
                'values': [['test']]
            }
            result = sheets_service.read_sheet('sheet_id', 'A1:B2')
            assert result == [['test']]

class TestSupabaseService:
    @pytest.fixture
    def supabase_service(self):
        return SupabaseService()

    def test_get_credential(self, supabase_service):
        """Test getting credentials from Supabase"""
        with patch('src.services.supabase.create_client') as mock_client:
            mock_client.return_value.table.return_value.select.return_value.eq.return_value.execute.return_value = Mock(
                data=[{'credential_value': 'test_value'}]
            )
            result = supabase_service.get_credential('test_service', 'test_key')
            assert result == 'test_value'

class TestInstagramService:
    @pytest.fixture
    def instagram_service(self):
        return InstagramService()

    def test_check_credentials(self, instagram_service):
        """Test Instagram credentials check"""
        with patch('requests.get') as mock_get:
            mock_get.return_value = Mock(status_code=200)
            assert instagram_service.check_credentials() is True
