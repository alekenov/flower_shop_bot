import os
import sys
import asyncio

# Добавляем путь к проекту
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.services.openai_service import OpenAIService

async def test_prompts():
    service = OpenAIService()
    
    # Тестовые сообщения
    test_messages = [
        # Проверка наличия
        "Какие розы у вас есть?",
        "Сколько стоят лилии?",
        
        # Заказы
        "Хочу заказать букет",
        "Можете доставить цветы?",
        
        # FAQ
        "До скольки вы работаете?",
        "Где находится магазин?",
        
        # Эмоции
        "Срочно нужны розы!",
        "Спасибо за отличный букет!",
        "К сожалению, нужен букет на похороны"
    ]
    
    print("\n=== Тестирование системы промптов ===\n")
    
    for message in test_messages:
        print(f"\nСообщение пользователя: {message}")
        print("-" * 50)
        
        # Определяем сценарий
        scenario = service._detect_scenario(message)
        print(f"Определенный сценарий: {scenario}")
        
        # Определяем эмоцию
        emotion = service._detect_emotion(message)
        print(f"Определенная эмоция: {emotion}")
        
        # Получаем промпт
        prompt = service._get_system_prompt(message)
        print("\nСгенерированный промпт:")
        print("-" * 30)
        print(prompt)
        print("-" * 30)
        
        # Тестируем ответ API
        try:
            response = await service.get_response(message)
            print("\nОтвет API:")
            print(response)
        except Exception as e:
            print(f"Ошибка при получении ответа: {str(e)}")
        
        print("\n" + "=" * 50)

if __name__ == "__main__":
    asyncio.run(test_prompts())
