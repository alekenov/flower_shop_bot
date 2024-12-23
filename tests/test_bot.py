"""
Tests for Telegram bot functionality
"""
import pytest
from unittest.mock import Mock, patch
from telegram import Update
from telegram.ext import CallbackContext

from src.bot.telegram_bot import TelegramBot
from src.services.supabase import SupabaseService

@pytest.fixture
def bot():
    return TelegramBot()

@pytest.fixture
def update():
    update = Mock(spec=Update)
    update.effective_chat.id = 123456789
    update.message.text = "Test message"
    return update

@pytest.fixture
def context():
    return Mock(spec=CallbackContext)

class TestBotCommands:
    async def test_start_command(self, bot, update, context):
        """Test /start command"""
        await bot.start(update, context)
        update.message.reply_text.assert_called_once()

    async def test_help_command(self, bot, update, context):
        """Test /help command"""
        await bot.help(update, context)
        update.message.reply_text.assert_called_once()

class TestBotResponses:
    async def test_text_message_handler(self, bot, update, context):
        """Test text message handling"""
        await bot.handle_message(update, context)
        assert update.message.reply_text.called

    async def test_invalid_message(self, bot, update, context):
        """Test handling of invalid messages"""
        update.message.text = None
        await bot.handle_message(update, context)
        update.message.reply_text.assert_called_with(
            "Извините, я понимаю только текстовые сообщения."
        )
