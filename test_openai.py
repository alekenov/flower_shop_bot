import os
import sys
import asyncio

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.openai_service import OpenAIService

async def test_openai():
    service = OpenAIService()
    try:
        response = await service.get_response("Какие цветы у вас есть в наличии?")
        print("Ответ от OpenAI:")
        print(response)
    except Exception as e:
        print(f"Ошибка при получении ответа: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai())
