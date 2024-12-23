"""
Integration tests for the Flower Shop Bot
"""
import pytest
from unittest.mock import Mock, patch

from src.bot.telegram_bot import TelegramBot
from src.services.openai import OpenAIService
from src.services.sheets import SheetsService
from src.services.supabase import SupabaseService

class TestBotIntegration:
    @pytest.fixture
    def bot(self):
        return TelegramBot()

    async def test_full_order_flow(self, bot):
        """Test complete order flow from start to finish"""
        with patch.multiple(
            'src.bot.telegram_bot',
            OpenAIService=Mock(),
            SheetsService=Mock(),
            SupabaseService=Mock()
        ):
            update = Mock()
            context = Mock()
            
            # Симулируем команду start
            update.message.text = "/start"
            await bot.start(update, context)
            
            # Симулируем заказ
            update.message.text = "Хочу заказать букет роз"
            await bot.handle_message(update, context)
            
            # Проверяем, что все сервисы были вызваны
            assert bot.openai_service.generate_response.called
            assert bot.sheets_service.update_sheet.called
            assert bot.supabase_service.store_order.called

    async def test_integration_with_openai(self, bot):
        """Test integration with OpenAI service"""
        with patch('src.services.openai.AsyncOpenAI') as mock_openai:
            mock_openai.return_value.chat.completions.create.return_value = Mock(
                choices=[Mock(message=Mock(content="Рекомендую букет из красных роз"))]
            )
            
            update = Mock()
            context = Mock()
            update.message.text = "Посоветуйте букет"
            
            await bot.handle_message(update, context)
            assert "букет из красных роз" in update.message.reply_text.call_args[0][0]

class TestDatabaseIntegration:
    def test_credentials_flow(self):
        """Test credentials management flow"""
        supabase = SupabaseService()
        
        # Проверяем получение учетных данных
        bot_token = supabase.get_credential('telegram', 'bot_token_test')
        assert bot_token is not None
        
        # Проверяем сохранение заказа
        order_data = {
            'user_id': 123456789,
            'product': 'Букет роз',
            'status': 'new'
        }
        order_id = supabase.store_order(order_data)
        assert order_id is not None
        
        # Проверяем получение заказа
        order = supabase.get_order(order_id)
        assert order['product'] == 'Букет роз'
