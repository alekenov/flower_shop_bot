import logging
from telegram import Bot
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
                        parse_mode='HTML'
                    )
                    logger.info(f"Message sent successfully: {result.message_id}")
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to send message to channel: {str(e)}")
                    # Попробуем отправить сообщение об ошибке в канал
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
                        logger.error(f"Failed to send error message: {inner_e}")
                finally:
                    self._message_queue.task_done()
        finally:
            self._is_processing = False
            logger.info("Finished processing message queue")
    
    async def log_interaction(self, user_id: int, username: str, question: str, answer: str, response_type: str = "Normal"):
        """Log bot interaction to the Telegram channel."""
        try:
            logger.info(f"Preparing to log interaction for user {user_id}")
            
            # Format the message
            message = (
                f"🤖 Bot Interaction Log\n\n"
                f"👤 User: {username} (ID: {user_id})\n"
                f"❓ Question:\n{question}\n\n"
                f"✍️ Answer:\n{answer}\n\n"
                f"📊 Response Type: {response_type}\n"
                f"-----------------------------------"
            )
            
            # Try direct send first
            try:
                logger.info("Attempting direct message send")
                await self.bot.send_message(
                    chat_id=self.log_channel_id,
                    text=message,
                    parse_mode='HTML'
                )
                logger.info("Direct message send successful")
                return
            except Exception as e:
                logger.error(f"Direct send failed, will try queue: {e}")
            
            # If direct send failed, try queue
            logger.info("Adding message to queue")
            await self._message_queue.put(message)
            logger.info("Creating queue processing task")
            asyncio.create_task(self._process_queue())
            logger.info("Queue processing task created")
            
        except Exception as e:
            logger.error(f"Failed to log to Telegram channel: {e}")
            logger.error(f"Channel ID: {self.log_channel_id}")
            logger.error(f"Bot Token (first 10 chars): {self.bot.token[:10]}...")
