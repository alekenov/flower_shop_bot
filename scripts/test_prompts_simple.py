import os
import sys

# Добавляем путь к проекту
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.prompts.system_prompts import get_prompt

def test_prompts():
    # Тестовые сценарии
    scenarios = ['availability', 'order', 'faq']
    emotions = ['positive', 'negative', 'neutral', 'urgent']
    
    print("\n=== Тестирование системы промптов ===\n")
    
    for scenario in scenarios:
        print(f"\n== Тестирование сценария: {scenario} ==")
        for emotion in emotions:
            print(f"\nЭмоция: {emotion}")
            print("-" * 50)
            
            prompt = get_prompt(scenario, emotion)
            
            # Считаем токены (приблизительно, 1 слово ~ 1.3 токена)
            words = len(prompt.split())
            tokens = int(words * 1.3)
            
            print(f"Промпт ({tokens} токенов):")
            print(prompt)
            print("-" * 50)

if __name__ == "__main__":
    test_prompts()
