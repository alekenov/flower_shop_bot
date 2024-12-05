from openai import OpenAI
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Создаем клиент OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def test_simple_request():
    try:
        # Делаем простой запрос
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Привет! Как дела?"}
            ]
        )
        print("Успешный ответ от API:")
        print(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Произошла ошибка:")
        print(f"Тип ошибки: {type(e)}")
        print(f"Текст ошибки: {str(e)}")

if __name__ == "__main__":
    print("Начинаем тест OpenAI API...")
    print(f"Используемый API ключ (первые 10 символов): {os.getenv('OPENAI_API_KEY')[:10]}...")
    test_simple_request()
