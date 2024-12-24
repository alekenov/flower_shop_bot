import requests
import logging
import time
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class MessageReactionHandler:
    def __init__(self):
        self.bot_token = "5261424288:AAE2QYTnulLeyd6BdanhhzxLFnhAbXvBI7w"
        self.chat_id = "-1002349745989"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.learning_topic_id = 145  # ID темы "Обучение бота"

    def get_message_info(self, message_id: int) -> Optional[Dict]:
        """Получает информацию о сообщении"""
        try:
            response = requests.get(
                f"{self.base_url}/getMessage",
                params={
                    "chat_id": self.chat_id,
                    "message_id": message_id
                }
            )
            
            if response.status_code == 200:
                return response.json()["result"]
            else:
                logger.error(f"Ошибка при получении сообщения {message_id}: {response.json()}")
                return None
        except Exception as e:
            logger.error(f"Исключение при получении сообщения {message_id}: {str(e)}")
            return None

    def forward_to_learning(self, message_id: int, from_topic_id: int) -> bool:
        """Пересылает сообщение в тему обучения"""
        try:
            # Пересылаем сообщение
            forward_response = requests.post(
                f"{self.base_url}/forwardMessage",
                json={
                    "chat_id": self.chat_id,
                    "from_chat_id": self.chat_id,
                    "message_id": message_id,
                    "message_thread_id": self.learning_topic_id
                }
            )
            
            if forward_response.status_code == 200:
                logger.info(f"Сообщение {message_id} переслано в тему обучения")
                
                # Отправляем пояснение
                comment_response = requests.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "message_thread_id": self.learning_topic_id,
                        "text": f"⚠️ Это сообщение получило дизлайк в теме {from_topic_id}. Требуется анализ и улучшение.",
                        "parse_mode": "Markdown"
                    }
                )
                
                if comment_response.status_code == 200:
                    logger.info("Комментарий к пересланному сообщению добавлен")
                    return True
                else:
                    logger.error(f"Ошибка при добавлении комментария: {comment_response.json()}")
            else:
                logger.error(f"Ошибка при пересылке сообщения: {forward_response.json()}")
            
            return False
        except Exception as e:
            logger.error(f"Исключение при пересылке сообщения: {str(e)}")
            return False

    def process_message(self, message_id: int, topic_id: int) -> None:
        """Обрабатывает сообщение и его реакции"""
        message = self.get_message_info(message_id)
        if not message:
            return

        # Проверяем наличие реакций
        if "reactions" in message:
            reactions = message["reactions"]["reactions"]
            likes = sum(1 for r in reactions if r["type"] == "emoji" and r["emoji"] == "👍")
            dislikes = sum(1 for r in reactions if r["type"] == "emoji" and r["emoji"] == "👎")
            
            logger.info(f"Сообщение {message_id}: 👍 {likes}, 👎 {dislikes}")
            
            if dislikes > likes:
                logger.info(f"Сообщение {message_id} будет перемещено в тему обучения")
                self.forward_to_learning(message_id, topic_id)

    def get_chat_messages(self) -> List[Dict]:
        """Получает последние сообщения из чата"""
        try:
            response = requests.get(
                f"{self.base_url}/getChat",
                params={
                    "chat_id": self.chat_id
                }
            )
            
            if response.status_code == 200:
                chat_info = response.json()["result"]
                logger.info(f"Информация о чате: {chat_info}")
                return chat_info
            else:
                logger.error(f"Ошибка при получении информации о чате: {response.json()}")
                return []
        except Exception as e:
            logger.error(f"Исключение при получении информации о чате: {str(e)}")
            return []

def main():
    handler = MessageReactionHandler()
    
    # Получаем информацию о чате
    chat_info = handler.get_chat_messages()
    logger.info("Завершение работы скрипта")

    # Список сообщений для проверки
    messages_to_check = [
        # (message_id, topic_id)
        (162, 161),  # Telegram Support
        (164, 163),  # WhatsApp Support
        (165, 143),  # Логи
        (166, 145),  # Обучение бота
        (167, 147),  # Ошибки и баги
        (168, 149),  # Instagram Support
        (169, 161),  # Telegram Support
        (170, 163)   # WhatsApp Support
    ]
    
    for message_id, topic_id in messages_to_check:
        logger.info(f"Проверка сообщения {message_id} в теме {topic_id}")
        handler.process_message(message_id, topic_id)
        time.sleep(1)  # Пауза между запросами

if __name__ == "__main__":
    main()
