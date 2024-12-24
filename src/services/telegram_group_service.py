import requests
import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class TelegramGroupService:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.main_chat_id = "-1002349745989"
        self.topic_descriptions = {
            "📝 Логи": """🔍 *Тема для логов системы*

• Автоматическая запись всех системных событий
• Мониторинг работы бота
• Отслеживание важных изменений
• История взаимодействий с пользователями""",

            "🎓 Обучение бота": """📚 *Пространство для обучения и улучшения бота*

• Новые команды и функции
• Улучшение существующих ответов
• Обсуждение качество ответов бота
• Предложения по развитию""",

            "🐛 Ошибки и баги": """🔧 *Отслеживание и исправление ошибок*

• Сообщения об ошибках
• Статус исправления
• Приоритетность багов
• Обсуждение решений""",

            "📸 Instagram Support": """📱 *Поддержка Instagram интеграции*

• Проблемы с постами
• Синхронизация контента
• Автопостинг
• Статистика и аналитика""",

            "📱 Telegram Support": """💬 *Поддержка Telegram функционала*

• Работа с сообщениями
• Управление группами
• Настройка уведомлений
• Интеграции с другими сервисами""",

            "💬 WhatsApp Support": """📲 *Поддержка WhatsApp интеграции*

• Статус соединения
• Обработка сообщений
• Автоматические ответы
• Массовые рассылки"""
        }

    def create_forum(self, title: str) -> Optional[int]:
        """
        Создает форум (супергруппу) с включенными темами
        """
        try:
            response = requests.post(
                f"{self.base_url}/createForumTopic",
                json={
                    "chat_id": self.main_chat_id,
                    "name": title,
                    "icon_color": 0x6FB9F0
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                topic_id = result["result"]["message_thread_id"]
                logger.info(f"Создана тема форума: {title}, ID: {topic_id}")
                return topic_id
            else:
                logger.error(f"Ошибка при создании темы форума: {response.json()}")
                return None
        except Exception as e:
            logger.error(f"Исключение при создании темы форума: {str(e)}")
            return None

    def send_message_to_topic(self, topic_id: int, message: str) -> bool:
        """
        Отправляет сообщение в конкретную тему форума
        """
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.main_chat_id,
                    "message_thread_id": topic_id,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Сообщение отправлено в тему {topic_id}")
                return True
            else:
                logger.error(f"Ошибка при отправке сообщения: {response.json()}")
                return False
        except Exception as e:
            logger.error(f"Исключение при отправке сообщения: {str(e)}")
            return False

    def create_support_structure(self) -> Dict[str, int]:
        """
        Создает структуру тем для службы поддержки и возвращает словарь с их ID
        """
        topic_ids = {}
        
        for topic_name in self.topic_descriptions.keys():
            topic_id = self.create_forum(topic_name)
            if topic_id:
                topic_ids[topic_name] = topic_id
                logger.info(f"Тема '{topic_name}' создана успешно")
                
                # Отправляем описание в тему
                if self.send_message_to_topic(topic_id, self.topic_descriptions[topic_name]):
                    logger.info(f"Описание для темы '{topic_name}' отправлено успешно")
                else:
                    logger.error(f"Не удалось отправить описание для темы '{topic_name}'")
            else:
                logger.error(f"Не удалось создать тему '{topic_name}'")
        
        return topic_ids

    def delete_topic(self, topic_id: int) -> bool:
        """
        Удаляет тему форума
        """
        try:
            response = requests.post(
                f"{self.base_url}/deleteForumTopic",
                json={
                    "chat_id": self.main_chat_id,
                    "message_thread_id": topic_id
                }
            )
            
            if response.status_code == 200:
                logger.info(f"Тема {topic_id} успешно удалена")
                return True
            else:
                logger.error(f"Ошибка при удалении темы: {response.json()}")
                return False
        except Exception as e:
            logger.error(f"Исключение при удалении темы: {str(e)}")
            return False

    def get_topics(self) -> List[Dict]:
        """
        Получает список всех тем форума
        """
        try:
            response = requests.post(
                f"{self.base_url}/getForumTopics",
                json={
                    "chat_id": self.main_chat_id
                }
            )
            
            if response.status_code == 200:
                return response.json()["result"]["topics"]
            else:
                logger.error(f"Ошибка при получении списка тем: {response.json()}")
                return []
        except Exception as e:
            logger.error(f"Исключение при получении списка тем: {str(e)}")
            return []

    def cleanup_duplicate_topics(self):
        """
        Удаляет дублирующиеся темы, оставляя только последние созданные
        """
        topics = self.get_topics()
        
        # Группируем темы по названиям
        topic_groups = {}
        for topic in topics:
            name = topic["name"]
            if name not in topic_groups:
                topic_groups[name] = []
            topic_groups[name].append(topic["message_thread_id"])
        
        # Удаляем все кроме последней созданной темы для каждого названия
        for name, topic_ids in topic_groups.items():
            if len(topic_ids) > 1:
                # Сортируем по ID (больший ID = более новая тема)
                topic_ids.sort()
                # Оставляем последнюю тему, удаляем остальные
                for topic_id in topic_ids[:-1]:
                    logger.info(f"Удаление дублирующейся темы '{name}' с ID {topic_id}")
                    self.delete_topic(topic_id)

def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Инициализация сервиса
    bot_token = "5261424288:AAE2QYTnulLeyd6BdanhhzxLFnhAbXvBI7w"
    service = TelegramGroupService(bot_token)
    
    # Создание структуры поддержки
    topic_ids = service.create_support_structure()
    
    # Удаляем дублирующиеся темы
    service.cleanup_duplicate_topics()

    # Вывод созданных тем и их ID
    logger.info("Созданные темы и их ID:")
    for topic_name, topic_id in topic_ids.items():
        logger.info(f"{topic_name}: {topic_id}")

if __name__ == "__main__":
    main()
