import asyncio
from src.services.docs_service import DocsService

async def test_bot_responses():
    service = DocsService()
    
    test_questions = [
        "Какие сейчас действуют акции?",
        "Расскажите про программу лояльности",
        "Какие условия для корпоративных клиентов?",
        "Как накопить баллы?",
        "Есть ли скидки для новых клиентов?"
    ]
    
    print("Тестирование ответов бота:\n")
    
    for question in test_questions:
        print(f"\nВопрос: {question}")
        response = await service.get_relevant_knowledge(question)
        print(f"Ответ: {response}\n")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_bot_responses())
