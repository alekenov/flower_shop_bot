from openai import OpenAI
from src.config.config import Config

class OpenAIService:
    def __init__(self):
        config = Config()
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        # Базовый промпт для бота
        self.system_prompt = """
        Ты - помощник цветочного магазина. Помогаешь клиентам с вопросами о ценах, доставке, наличии цветов и графике работы.
        Отвечай кратко и по делу.
        """

    async def get_response(self, user_message: str) -> str:
        """
        Получает ответ от OpenAI на сообщение пользователя
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Возвращаемся к GPT-3.5-turbo
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Debug - Full error: {str(e)}")
            raise Exception(f"Error getting OpenAI response: {str(e)}")
