import logging
from telegram import Bot
from telegram.constants import ParseMode
from src.config.config import Config
import asyncio

logger = logging.getLogger(__name__)

class ChannelLogger:
    def __init__(self):
        """Initialize the channel logger."""
        try:
            config = Config()
            self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
            self.log_channel_id = config.TELEGRAM_LOG_CHANNEL_ID
            self._message_queue = asyncio.Queue()
            self._is_processing = False
            logger.info(f"ChannelLogger initialized with channel ID: {self.log_channel_id}")
        except Exception as e:
            logger.error(f"Error initializing ChannelLogger: {e}")
            raise
    
    async def _process_queue(self):
        """Process messages in the queue."""
        if self._is_processing:
            logger.debug("Queue is already being processed")
            return
        
        self._is_processing = True
        logger.info("Starting to process message queue")
        try:
            while not self._message_queue.empty():
                message = await self._message_queue.get()
                try:
                    logger.info(f"Attempting to send message to channel {self.log_channel_id}")
                    result = await self.bot.send_message(
                        chat_id=self.log_channel_id,
                        text=message,
                        parse_mode=ParseMode.HTML
                    )
                    logger.info(f"Message sent successfully: {result.message_id}")
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send message to channel: {str(e)}")
                    try:
                        error_message = (
                            "⚠️ Error in bot logging system:\n"
                            f"Channel ID: {self.log_channel_id}\n"
                            f"Error: {str(e)}\n"
                            "Please check bot permissions in the channel"
                        )
                        await self.bot.send_message(
                            chat_id=self.log_channel_id,
                            text=error_message
                        )
                    except Exception as inner_e:
                        logger.error(f"Failed to send error message: {str(inner_e)}")
                finally:
                    self._message_queue.task_done()
        finally:
            self._is_processing = False
            logger.info("Finished processing message queue")
    
    async def log_message(self, user_message, bot_response):
        """Log a message to the channel."""
        try:
            user = user_message.from_user
            log_text = (
                f"👤 <b>User:</b> {user.first_name} ({user.id})\n"
                f"📝 <b>Message:</b> {user_message.text}\n"
                f"🤖 <b>Response:</b> {bot_response}\n"
                f"⏰ <b>Time:</b> {user_message.date.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            await self._message_queue.put(log_text)
            asyncio.create_task(self._process_queue())
            logger.info(f"Message from user {user.id} queued for logging")
            
        except Exception as e:
            logger.error(f"Error logging message: {str(e)}")
