import asyncio
import logging
from services.docs_service import DocsService
import sys
from temp_config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    try:
        docs_service = DocsService()
        await docs_service.create_initial_structure()
        logger.info("Successfully initialized knowledge base structure")
    except Exception as e:
        logger.error(f"Failed to initialize knowledge base: {e}")

if __name__ == "__main__":
    asyncio.run(main())
