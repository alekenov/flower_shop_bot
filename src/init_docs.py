import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.services.docs_service import DocsService

async def main():
    """Инициализация документа базы знаний."""
    docs_service = DocsService()
    await docs_service.create_initial_structure()

if __name__ == "__main__":
    asyncio.run(main())
