import requests
import logging
import json
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class FeedbackService:
    def __init__(self):
        self.bot_token = "5261424288:AAE2QYTnulLeyd6BdanhhzxLFnhAbXvBI7w"
        self.chat_id = "-1002349745989"
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.learning_topic_id = 145

    def send_message_with_buttons(self, topic_id: int, text: str) -> None:
        """Отправляет сообщение с кнопками для оценки"""
        keyboard = {
            "inline_keyboard": [[
                {"text": "👍", "callback_data": f"like_{topic_id}"},
                {"text": "👎", "callback_data": f"dislike_{topic_id}"}
            ]]
        }

        try:
            # Сначала удаляем старое сообщение, если оно есть
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "message_thread_id": topic_id,
                    "text": f"{text}\n\n_Пожалуйста, оцените это сообщение:_",
                    "reply_markup": json.dumps(keyboard),
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Сообщение с кнопками отправлено в тему {topic_id}")
            else:
                logger.error(f"Ошибка при отправке сообщения: {response.json()}")
        except Exception as e:
            logger.error(f"Исключение при отправке сообщения: {str(e)}")

def main():
    service = FeedbackService()
    
    # Список тем и сообщений
    messages = [
        (143, "🔍 *Тестовое сообщение в логах*\nПроверка системы логирования"),
        (145, "📚 *Тест обучения бота*\nКак вам качество ответов бота?"),
        (147, "🔧 *Тестирование системы*\nЗамечены ли какие-либо ошибки?"),
        (149, "📱 *Проверка Instagram интеграции*\nРаботает ли синхронизация с Instagram?"),
        (161, "💬 *Тест Telegram функционала*\nПроверка работы уведомлений и команд"),
        (163, "📲 *Проверка WhatsApp интеграции*\nТестирование подключения к WhatsApp")
    ]
    
    # Отправляем сообщения с кнопками во все темы
    for topic_id, message in messages:
        service.send_message_with_buttons(topic_id, message)
        time.sleep(1)  # Пауза между отправками

if __name__ == "__main__":
    main()
