import os
import json
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
            credentials_info = json.loads(config.GOOGLE_CREDENTIALS)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
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

## 1. Основная информация о магазине
### Часы работы
- Магазин работает ежедневно с 9:00 до 21:00
- Доставка осуществляется с 9:00 до 20:00
- Прием заказов круглосуточно через бота

### Контакты
- Телефон: +7 (XXX) XXX-XX-XX
- Email: info@cvety.kz
- Instagram: @cvety.kz
- Telegram: @cvetykz_bot

### Локации
- Главный магазин: [адрес]
- Пункты выдачи: [адреса]

## 2. Каталог и цены
### 2.1 Розы
#### Виды роз
- Классические розы (40, 50, 60, 70 см)
- Пионовидные розы
- Кустовые розы
- Премиум сорта

#### Цены на розы
- 40 см: от X тенге/шт
- 50 см: от X тенге/шт
- 60 см: от X тенге/шт
- 70 см: от X тенге/шт

#### Особенности
- Свежие поставки каждый день
- Гарантия свежести 7 дней
- Возможность выбора цвета

### 2.2 Букеты
#### Категории букетов
- Монобукеты из роз
- Смешанные букеты
- Авторские композиции
- Букеты на праздники

#### Ценовые диапазоны
- Экономичные: до X тенге
- Стандарт: X-Y тенге
- Премиум: от Y тенге

### 2.3 Комнатные растения
- Виды растений
- Уход и рекомендации
- Цены и доставка

### 2.4 Сезонные предложения
[Обновляется автоматически]

## 3. Доставка
### 3.1 Стандартная доставка
#### Зоны доставки
- Центр города: X тенге
- Спальные районы: Y тенге
- Пригород: Z тенге

#### Время доставки
- В течение дня: 2-3 часа
- Предварительный заказ: точное время

### 3.2 Срочная доставка
- Доставка за 1 час
- Условия срочной доставки
- Дополнительная стоимость

### 3.3 Предварительные заказы
- Бронирование даты и времени
- Специальные условия
- Гарантии доставки

## 4. Оплата
### Способы оплаты
- Наличные при получении
- Банковские карты
- Kaspi переводы
- Корпоративные счета

### Условия оплаты
- Предоплата для предварительных заказов
- Оплата при получении
- Корпоративные условия

### Возврат и гарантии
- Условия возврата
- Гарантия свежести
- Замена букета

## 5. Специальные предложения
### 5.1 Текущие акции
[Обновляется еженедельно]

### 5.2 Программа лояльности
- Система баллов
- Скидки постоянным клиентам
- Особые условия

### 5.3 Корпоративным клиентам
- Специальные условия
- Документооборот
- Отсрочка платежа

## 6. FAQ (Частые вопросы)
[Автоматически обновляемый раздел]

## 7. Активные вопросы
[Новые вопросы для обработки]

## 8. Примеры диалогов
### 8.1 Стандартные ситуации
#### Пример 1: Заказ букета
В: Хочу заказать букет роз
О: Конечно! Я помогу вам выбрать идеальный букет. Какой длины розы вы предпочитаете? У нас есть розы 40, 50, 60 и 70 см.

#### Пример 2: Доставка
В: Сколько стоит доставка в [район]?
О: Доставка в [район] стоит X тенге. Среднее время доставки 2-3 часа. Хотите оформить заказ?

### 8.2 Сложные случаи
[Примеры решения нестандартных ситуаций]

### 8.3 Успешные решения
[Примеры особо удачных диалогов]

## 9. Метаданные
- Версия базы знаний: 1.0
- Дата последнего обновления: [автообновление]
- Количество обработанных вопросов: [автообновление]
- Процент успешных ответов: [автообновление]"""

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

    async def get_section_content(self, section_title: str) -> str:
        """Получение содержимого конкретного раздела."""
        try:
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            section_start = self._find_section_index(doc, section_title)
            if section_start == -1:
                logger.error(f"Section {section_title} not found")
                return ""
            
            next_section_start = -1
            full_text = ""
            current_index = 1
            
            # Ищем следующий заголовок того же или более высокого уровня
            for element in content:
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        text = part.get('textRun', {}).get('content', '')
                        if current_index > section_start and text.strip().startswith('#'):
                            next_section_start = current_index
                            break
                        current_index += len(text)
            
            # Получаем текст раздела
            current_index = 1
            is_in_section = False
            for element in content:
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        text = part.get('textRun', {}).get('content', '')
                        if current_index == section_start:
                            is_in_section = True
                        if next_section_start != -1 and current_index >= next_section_start:
                            is_in_section = False
                        if is_in_section:
                            full_text += text
                        current_index += len(text)
            
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"Failed to get section content: {e}")
            raise

    async def update_section(self, section_title: str, new_content: str):
        """Обновление содержимого раздела."""
        try:
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            section_start = self._find_section_index(doc, section_title)
            
            if section_start == -1:
                logger.error(f"Section {section_title} not found")
                return
            
            # Находим конец раздела
            content = doc.get('body', {}).get('content', [])
            next_section_start = -1
            current_index = 1
            
            for element in content:
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        text = part.get('textRun', {}).get('content', '')
                        if current_index > section_start and text.strip().startswith('#'):
                            next_section_start = current_index
                            break
                        current_index += len(text)
            
            # Создаем запросы на обновление
            requests = []
            
            # Если нашли следующий раздел, удаляем текущий контент
            if next_section_start != -1:
                requests.append({
                    'deleteContentRange': {
                        'range': {
                            'startIndex': section_start + len(section_title) + 1,
                            'endIndex': next_section_start
                        }
                    }
                })
            
            # Добавляем новый контент
            requests.append({
                'insertText': {
                    'location': {
                        'index': section_start + len(section_title) + 1
                    },
                    'text': f"\n{new_content}\n"
                }
            })
            
            # Выполняем запросы
            result = self.service.documents().batchUpdate(
                documentId=self.knowledge_base_doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Successfully updated section {section_title}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update section: {e}")
            raise

    async def add_faq_item(self, question: str, answer: str):
        """Добавление нового вопроса и ответа в раздел FAQ."""
        try:
            faq_content = await self.get_section_content("## 6. FAQ")
            new_faq_item = f"\n### Вопрос: {question}\nОтвет: {answer}\n"
            
            if not faq_content:
                new_content = new_faq_item
            else:
                new_content = faq_content + "\n" + new_faq_item
            
            await self.update_section("## 6. FAQ", new_content)
            logger.info(f"Successfully added new FAQ item: {question}")
            
        except Exception as e:
            logger.error(f"Failed to add FAQ item: {e}")
            raise

    async def update_metadata(self):
        """Обновление метаданных документа."""
        try:
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            
            # Получаем текущую статистику
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            faq_content = await self.get_section_content("## 6. FAQ")
            faq_count = faq_content.count("### Вопрос:")
            
            metadata_content = f"""- Версия базы знаний: 1.0
- Дата последнего обновления: {current_time}
- Количество FAQ: {faq_count}"""
            
            await self.update_section("## 9. Метаданные", metadata_content)
            logger.info("Successfully updated metadata")
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            raise
