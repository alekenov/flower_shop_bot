#!/usr/bin/env python3
import asyncio
import sys
import os

# Добавляем путь к директории src
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)

from services.docs_service import DocsService

async def main():
    """Инициализация базы знаний в Google Docs."""
    try:
        docs_service = DocsService()
        doc_id = await docs_service.create_knowledge_base_doc()
        print(f"Successfully created knowledge base document with ID: {doc_id}")
        print("Please visit the following URL to view and edit the document:")
        print(f"https://docs.google.com/document/d/{doc_id}/edit")
    except Exception as e:
        print(f"Error creating knowledge base: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
