import os
import sys
import logging
import asyncio
import socket
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import our bot class
from telegram_bot import TelegramBot

def is_bot_running():
    """Check if another instance of the bot is running"""
    try:
        # Try to create a socket on port 12345
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 12345))
        sock.listen(1)
        return False
    except socket.error:
        return True
    
async def main():
    """Main function to run the bot in polling mode"""
    # Check if bot is already running
    if is_bot_running():
        logger.error("Another instance of the bot is already running!")
        sys.exit(1)
        
    try:
        # Set environment variables
        os.environ['ENVIRONMENT'] = 'dev'
        
        # Create bot instance
        bot = TelegramBot()
        
        # Start polling
        logger.info("Starting bot in polling mode...")
        application = bot.application
        
        # Run the bot until you press Ctrl-C
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        # Keep the bot running
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Stopping bot...")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}", exc_info=True)
        raise
    finally:
        # Properly shut down
        try:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}", exc_info=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {str(e)}", exc_info=True)
        sys.exit(1)
