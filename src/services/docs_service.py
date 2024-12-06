import os
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.config.config import Config

logger = logging.getLogger(__name__)

class DocsService:
    """Сервис для работы с Google Docs."""

    def __init__(self):
        """Инициализация сервиса Google Docs."""
        try:
            config = Config()
            credentials = service_account.Credentials.from_service_account_file(
                config.GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=['https://www.googleapis.com/auth/documents']
            )
            self.service = build('docs', 'v1', credentials=credentials)
            self.knowledge_base_doc_id = config.GOOGLE_DOCS_KNOWLEDGE_BASE_ID
            logger.info("Successfully initialized Google Docs service")
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs service: {e}")
            raise

    async def add_unanswered_question(self, question: str, user_id: int, bot_response: str = None, response_type: str = "Нет ответа"):
        """Добавление нового вопроса в секцию активных вопросов."""
        try:
            # Получаем документ
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            
            # Ищем индекс раздела активных вопросов
            active_questions_index = self._find_section_index(doc, "## Активные вопросы")
            
            if active_questions_index == -1:
                logger.error("Active questions section not found")
                # Попробуем найти начало документа
                active_questions_index = 1
            
            # Добавляем новый вопрос с датой и временем
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            question_text = f"""

[Новый вопрос для обучения]
Дата: {current_time}
От пользователя: {user_id}
Тип: {response_type}

Вопрос: 
{question}

Ответ бота:
{bot_response if bot_response else "Нет ответа"}

Требуемые действия:
- [ ] Проанализировать вопрос
- [ ] Добавить информацию в базу знаний
- [ ] Улучшить промпт бота
- [ ] Проверить ответ после обучения

---"""
            
            # Создаем запрос на вставку текста
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': active_questions_index + len("## Активные вопросы")
                        },
                        'text': question_text
                    }
                }
            ]
            
            # Выполняем запрос
            result = self.service.documents().batchUpdate(
                documentId=self.knowledge_base_doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Successfully added question from user {user_id}: {result}")
            
        except Exception as e:
            logger.error(f"Failed to add unanswered question: {e}")
            logger.error(f"Document ID: {self.knowledge_base_doc_id}")
            raise

    def _find_section_index(self, doc: dict, section_title: str) -> int:
        """Поиск индекса начала секции по заголовку."""
        content = doc.get('body', {}).get('content', [])
        full_text = ""
        current_index = 1  # Google Docs начинает с индекса 1
        
        for element in content:
            if 'paragraph' in element:
                for part in element['paragraph'].get('elements', []):
                    text = part.get('textRun', {}).get('content', '')
                    if section_title in text:
                        return current_index
                    full_text += text
                    current_index += len(text)
        
        return -1

    async def get_knowledge_base(self) -> str:
        """Получение базы знаний."""
        try:
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            full_text = ""
            for element in content:
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        text = part.get('textRun', {}).get('content', '')
                        full_text += text
            
            return full_text
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base: {e}")
            raise

    async def create_initial_structure(self):
        """Создание начальной структуры документа базы знаний."""
        try:
            initial_content = """# База знаний Cvety.kz 🌸

## Активные вопросы
[Новые вопросы будут добавляться здесь автоматически]

---

## Обработанные вопросы и ответы

### 1. Заказы и доставка
В: Как сделать заказ?
О: Просто напишите боту, какие цветы вы хотите заказать. Бот поможет выбрать цветы, укажет цены и оформит заказ.

В: Какие способы доставки доступны?
О: Мы доставляем цветы по всему городу с 9:00 до 21:00. Доставка осуществляется в течение 2-3 часов после оформления заказа.

### 2. Ассортимент и цены
В: Как узнать, какие цветы есть в наличии?
О: Напишите боту "покажи ассортимент" или "какие цветы есть?", и он покажет актуальный список цветов с ценами.

В: Можно ли заказать букет заранее?
О: Да, вы можете оформить предварительный заказ. Укажите боту желаемую дату и время доставки при оформлении заказа.

### 3. Оплата
В: Какие способы оплаты доступны?
О: Принимаем оплату наличными при доставке и банковскими картами через бот.

В: Когда нужно оплачивать заказ?
О: При оформлении заказа через бот. Мы начинаем готовить букет после подтверждения оплаты.

### 4. Дополнительные услуги
В: Можно ли добавить к букету открытку?
О: Да, при оформлении заказа вы можете добавить открытку с вашим текстом бесплатно.

В: Есть ли упаковка для букетов?
О: Все наши букеты красиво упаковываются по умолчанию. Доступны различные варианты упаковки на ваш выбор."""

            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1
                        },
                        'text': initial_content
                    }
                }
            ]
            
            self.service.documents().batchUpdate(
                documentId=self.knowledge_base_doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info("Successfully created initial document structure")
            
        except Exception as e:
            logger.error(f"Failed to create initial structure: {e}")
            raise
