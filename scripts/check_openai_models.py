import os
import openai
from src.utils.credentials_manager import credentials_manager

async def main():
    try:
        # Получаем API ключ из Supabase
        api_key = credentials_manager.get_credential('openai', 'api_key')
        openai.api_key = api_key
        
        print(f"\nUsing API key: {api_key[:8]}...")  

        # Получаем список моделей
        print("\nFetching available models...")
        models = openai.Model.list()

        # Анализируем доступные модели
        print("\nAvailable Models:")
        print("=" * 50)
        
        # Фильтруем только GPT модели
        gpt_models = [m for m in models.data if any(x in m.id for x in ['gpt-4', 'gpt-3.5'])]
        
        # Сортируем модели
        gpt_models.sort(key=lambda x: (
            '4' if 'gpt-4' in x.id else '3.5',  # Сначала GPT-4, потом GPT-3.5
            'turbo' in x.id,  # Turbo версии выше
            x.created  # Более новые версии выше
        ), reverse=True)

        for model in gpt_models:
            print(f"\nModel ID: {model.id}")
            print(f"Created: {model.created}")
            print(f"Owned By: {model.owned_by}")
            print("-" * 30)
    
    except Exception as e:
        print(f"Error: {str(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            traceback.print_tb(e.__traceback__)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
