import requests
import logging
import time
from typing import Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ReactionAnalyzer:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id
        self.learning_topic_id = 145  # ID темы "Обучение бота"

    def get_message_reactions(self, message_id: int) -> Tuple[int, int]:
        """
        Получает количество лайков и дизлайков для сообщения
        Возвращает (likes, dislikes)
        """
        try:
            response = requests.get(
                f"{self.base_url}/getMessage",
                params={
                    "chat_id": self.chat_id,
                    "message_id": message_id
                }
            )
            
            if response.status_code == 200:
                message = response.json()["result"]
                if "reactions" in message:
                    reactions = message["reactions"]
                    likes = sum(1 for r in reactions if r["type"] == "emoji" and r["emoji"] == "👍")
                    dislikes = sum(1 for r in reactions if r["type"] == "emoji" and r["emoji"] == "👎")
                    return likes, dislikes
                return 0, 0
            else:
                logger.error(f"Ошибка при получении сообщения: {response.json()}")
                return 0, 0
        except Exception as e:
            logger.error(f"Исключение при получении реакций: {str(e)}")
            return 0, 0

    def forward_message(self, message_id: int, from_topic_id: int) -> bool:
        """
        Пересылает сообщение в тему для обучения бота
        """
        try:
            response = requests.post(
                f"{self.base_url}/forwardMessage",
                json={
                    "chat_id": self.chat_id,
                    "message_thread_id": self.learning_topic_id,
                    "from_chat_id": self.chat_id,
                    "message_id": message_id
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Сообщение {message_id} переслано в тему обучения")
                
                # Добавляем комментарий о том, откуда пришло сообщение
                self.send_message(
                    self.learning_topic_id,
                    f"⚠️ Это сообщение получило дизлайк в теме {from_topic_id}. Требуется анализ и улучшение."
                )
                return True
            else:
                logger.error(f"Ошибка при пересылке сообщения: {response.json()}")
                return False
        except Exception as e:
            logger.error(f"Исключение при пересылке сообщения: {str(e)}")
            return False

    def send_message(self, topic_id: int, text: str) -> Optional[int]:
        """
        Отправляет новое сообщение в тему
        """
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "message_thread_id": topic_id,
                    "text": text,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code == 200:
                return response.json()["result"]["message_id"]
            else:
                logger.error(f"Ошибка при отправке сообщения: {response.json()}")
                return None
        except Exception as e:
            logger.error(f"Исключение при отправке сообщения: {str(e)}")
            return None

    def analyze_topic_messages(self, topic_id: int):
        """
        Анализирует сообщения в теме и обрабатывает их в зависимости от реакций
        """
        try:
            # Получаем обновления
            response = requests.get(
                f"{self.base_url}/getUpdates",
                params={
                    "offset": -1,  # Получаем последние обновления
                    "limit": 100    # Максимальное количество сообщений
                }
            )
            
            if response.status_code == 200:
                updates = response.json()["result"]
                for update in updates:
                    if "message" in update:
                        msg = update["message"]
                        if "message_thread_id" in msg and msg["message_thread_id"] == topic_id:
                            message_id = msg["message_id"]
                            likes, dislikes = self.get_message_reactions(message_id)
                            
                            if dislikes > likes:
                                logger.info(f"Сообщение {message_id} получило больше дизлайков ({dislikes}>{likes})")
                                self.forward_message(message_id, topic_id)
            else:
                logger.error(f"Ошибка при получении обновлений: {response.json()}")
        except Exception as e:
            logger.error(f"Исключение при анализе темы: {str(e)}")

def main():
    # Конфигурация
    BOT_TOKEN = "5261424288:AAE2QYTnulLeyd6BdanhhzxLFnhAbXvBI7w"
    CHAT_ID = "-1002349745989"
    
    analyzer = ReactionAnalyzer(BOT_TOKEN, CHAT_ID)
    
    # Список тем для анализа
    topics = [
        (143, "📝 Логи"),
        (145, "🎓 Обучение бота"),
        (147, "🐛 Ошибки и баги"),
        (149, "📸 Instagram Support"),
        (161, "📱 Telegram Support"),
        (163, "💬 WhatsApp Support")
    ]
    
    # Анализируем каждую тему
    for topic_id, topic_name in topics:
        logger.info(f"Анализ темы: {topic_name}")
        analyzer.analyze_topic_messages(topic_id)
        time.sleep(2)  # Пауза между темами

if __name__ == "__main__":
    main()
