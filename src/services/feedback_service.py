import logging
from typing import Dict, Optional, Tuple
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from services.config_service import ConfigService
from services.postgres_service import PostgresService

logger = logging.getLogger(__name__)

class FeedbackService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = ConfigService()
        self.db = PostgresService()
        self.topics = {}  # Инициализируем пустым словарем

    async def initialize(self):
        """Асинхронная инициализация"""
        await self._load_topics()

    async def _load_topics(self):
        """Загрузка тем форума напрямую из Telegram"""
        try:
            chat_id = await self.config.get_config_async('log_group_id', service='telegram')
            forum_topics = await self.bot.get_forum_topics(chat_id=chat_id)
            
            logger.info(f"Получаем темы из группы {chat_id}")
            self.topics = {}
            
            for topic in forum_topics:
                self.topics[topic.name] = topic.message_thread_id
                logger.info(f"Загружена тема: {topic.name} (ID: {topic.message_thread_id})")
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке тем форума: {str(e)}", exc_info=True)
            # Если не удалось загрузить из Telegram, используем темы из базы
            query = "SELECT topic_id, name FROM forum_topics;"
            result = await self.db.fetch_all(query)
            self.topics = {row['name']: row['topic_id'] for row in result}
            logger.info(f"Загружены темы из базы: {self.topics}")

    async def add_feedback_buttons(self, chat_id: str, topic_id: Optional[int], message_id: int) -> None:
        """Добавляет кнопки для оценки к сообщению в логах"""
        if not topic_id:
            logger.error("topic_id не указан")
            return
            
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍", callback_data=f"like_{topic_id}_{message_id}"),
                InlineKeyboardButton("👎", callback_data=f"dislike_{topic_id}_{message_id}")
            ]
        ])

        try:
            await self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard
            )
            logger.info(f"Добавлены кнопки оценки к сообщению {message_id} в теме {topic_id}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении кнопок: {str(e)}")

    async def update_message_buttons(self, chat_id: str, message_id: int, topic_id: Optional[int], action: str) -> None:
        """Обновляет кнопки сообщения после нажатия"""
        if not topic_id:
            logger.error("topic_id не указан")
            return
            
        try:
            if action == "like":
                new_keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Хороший пример", callback_data=f"liked_{topic_id}_{message_id}")
                ]])
            else:  # dislike
                new_keyboard = InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отправлено на доработку", callback_data=f"done_{topic_id}_{message_id}")
                ]])

            await self.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=new_keyboard
            )
            logger.info(f"Кнопки сообщения {message_id} обновлены")
        except Exception as e:
            logger.error(f"Ошибка при обновлении кнопок: {str(e)}")

    async def forward_message(self, chat_id: str, message_id: int, from_topic_id: int, to_topic_id: int, comment: str) -> bool:
        """Пересылает сообщение в другую тему"""
        try:
            # Пересылаем сообщение
            forwarded_msg = await self.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=message_id,
                message_thread_id=to_topic_id
            )
            
            if forwarded_msg:
                logger.info(f"Сообщение {message_id} переслано из темы {from_topic_id} в тему {to_topic_id}")
                
                # Отправляем пояснение
                await self.bot.send_message(
                    chat_id=chat_id,
                    message_thread_id=to_topic_id,
                    text=comment,
                    parse_mode="Markdown"
                )
                logger.info("Комментарий к пересланному сообщению добавлен")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения: {str(e)}")
            return False

    async def handle_like(self, chat_id: str, message_id: int, topic_id: Optional[int]) -> Tuple[bool, str]:
        """Обрабатывает лайк сообщения"""
        try:
            # Получаем ID темы для хороших примеров
            good_examples_topic = await self.get_topic_id('🎓 Обучение бота')
            if not good_examples_topic:
                logger.error("Не найдена тема 'Обучение бота'")
                return False, "Ошибка: тема не найдена"

            # Пересылаем сообщение
            forwarded_msg = await self.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=message_id,
                message_thread_id=good_examples_topic
            )
            
            logger.info(
                f"Сообщение оценено положительно:\n"
                f"ID сообщения: {message_id}\n"
                f"Из темы: {topic_id}\n"
                f"В тему: Обучение бота (ID: {good_examples_topic})"
            )
            
            # Добавляем комментарий
            await self.bot.send_message(
                chat_id=chat_id,
                message_thread_id=good_examples_topic,
                reply_to_message_id=forwarded_msg.message_id,
                text="✅ Сообщение отмечено как хороший пример ответа"
            )
            
            return True, "Спасибо за положительную оценку! 👍"
            
        except Exception as e:
            logger.error(f"Ошибка при обработке лайка: {str(e)}", exc_info=True)
            return False, "Произошла ошибка при обработке оценки"

    async def handle_dislike(self, chat_id: str, message_id: int, topic_id: Optional[int]) -> Tuple[bool, str]:
        """Обрабатывает дизлайк сообщения"""
        try:
            # Получаем ID темы для сообщений на доработку
            improvement_topic = await self.get_topic_id('🐛 Ошибки и баги')
            if not improvement_topic:
                logger.error("Не найдена тема 'Ошибки и баги'")
                return False, "Ошибка: тема не найдена"

            # Пересылаем сообщение
            forwarded_msg = await self.bot.forward_message(
                chat_id=chat_id,
                from_chat_id=chat_id,
                message_id=message_id,
                message_thread_id=improvement_topic
            )
            
            logger.info(
                f"Сообщение оценено отрицательно:\n"
                f"ID сообщения: {message_id}\n"
                f"Из темы: {topic_id}\n"
                f"В тему: Ошибки и баги (ID: {improvement_topic})"
            )
            
            # Добавляем комментарий
            await self.bot.send_message(
                chat_id=chat_id,
                message_thread_id=improvement_topic,
                reply_to_message_id=forwarded_msg.message_id,
                text="❌ Сообщение отмечено как требующее доработки"
            )
            
            return True, "Спасибо за отзыв! Мы улучшим ответы 👍"
            
        except Exception as e:
            logger.error(f"Ошибка при обработке дизлайка: {str(e)}", exc_info=True)
            return False, "Произошла ошибка при обработке оценки"

    async def send_to_logs(self, message: str) -> None:
        """Отправка сообщения в тему логов"""
        log_topic_id = self.topics.get('📝 Логи')
        if not log_topic_id:
            logger.error("ID темы логов не найден")
            return
            
        await self.send_message_with_buttons(log_topic_id, message)

    async def get_topic_id(self, topic_name: str) -> Optional[int]:
        """Получает ID темы по её имени"""
        try:
            if not self.topics:
                await self._load_topics()
            return self.topics.get(topic_name)
        except Exception as e:
            logger.error(f"Ошибка при получении ID темы: {str(e)}")
            return None
