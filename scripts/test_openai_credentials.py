import os
import openai
from src.services.credentials_service import credentials_service

async def test_openai_credentials():
    try:
        # Получаем API ключ из Supabase
        api_key = await credentials_service.get_credential('openai', 'api_key')
        openai.api_key = api_key
        
        # Тестируем подключение
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Say 'Hello World'"}]
        )
        
        print("Тест успешен! Ответ от OpenAI:", completion.choices[0].message.content)
        return True
    except Exception as e:
        print(f"Ошибка при тестировании учетных данных OpenAI: {str(e)}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_openai_credentials())
