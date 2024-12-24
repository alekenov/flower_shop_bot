# ID документа базы знаний
KNOWLEDGE_BASE_DOC_ID = "18pFk1BJxefIE89GdFxRRPKy3LGGOpFwam5nhye6KhCg"

import os
import json
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import psycopg2
from psycopg2.extras import DictCursor
from typing import Optional

logger = logging.getLogger(__name__)

# Конфигурация подключения к Supabase
SUPABASE_CONFIG = {
    'host': 'aws-0-eu-central-1.pooler.supabase.com',
    'port': '6543',
    'user': 'postgres.dkohweivbdwweyvyvcbc',
    'password': 'vigkif-nesJy2-kivraq',
    'database': 'postgres'
}

class DocsService:
    """Сервис для работы с Google Docs."""

    def __init__(self):
        """Инициализация сервиса Google Docs."""
        try:
            # Подключаемся к базе данных
            conn = psycopg2.connect(
                host=SUPABASE_CONFIG['host'],
                port=SUPABASE_CONFIG['port'],
                user=SUPABASE_CONFIG['user'],
                password=SUPABASE_CONFIG['password'],
                database=SUPABASE_CONFIG['database']
            )
            conn.autocommit = True

            # Получаем учетные данные Google и ID документа
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Получаем service account
                cur.execute(
                    """
                    SELECT credential_value 
                    FROM credentials 
                    WHERE service_name = 'google' AND credential_key = 'service_account'
                    """
                )
                service_account_result = cur.fetchone()
                
                # Получаем ID документа
                cur.execute(
                    """
                    SELECT credential_value 
                    FROM credentials 
                    WHERE service_name = 'google' AND credential_key = 'docs_knowledge_base_id'
                    """
                )
                doc_id_result = cur.fetchone()
                
            if not service_account_result or not doc_id_result:
                raise Exception("Не найдены учетные данные Google или ID документа")

            # Загружаем service account
            service_account_info = json.loads(service_account_result[0])
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/documents.readonly']
            )
            
            # Сохраняем ID документа
            self.knowledge_base_doc_id = doc_id_result[0]
            
            # Создаем сервис
            self.service = build('docs', 'v1', credentials=self.credentials)
            
            # Загружаем документ при инициализации
            self.sections = {}
            self._load_document()
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs service: {e}")
            raise

    def _load_document(self):
        """Загружает и индексирует документ."""
        try:
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            if not content:
                logger.error("Не удалось получить содержимое документа")
                return

            # Извлекаем текст и разбиваем на секции
            current_section = None
            current_content = []

            for element in content:
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        if text := part.get('textRun', {}).get('content'):
                            if text.startswith('## '):
                                if current_section:
                                    self.sections[current_section] = '\n'.join(current_content)
                                current_section = text.strip()
                                current_content = []
                            else:
                                current_content.append(text)

            if current_section:
                self.sections[current_section] = '\n'.join(current_content)

            logger.info(f"Загружено {len(self.sections)} разделов")
            for section in self.sections:
                logger.info(f"Раздел: {section}")

        except Exception as e:
            logger.error(f"Ошибка при загрузке документа: {e}")

    async def add_unanswered_question(self, question: str, user_id: int, bot_response: str = None, response_type: str = "Нет ответа"):
        """Добавление нового вопроса в секцию активных вопросов."""
        try:
            # Получаем документ
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            
            # Ищем индекс раздела активных вопросов
            active_questions_index = self._find_section_index(doc, "## 7. Активные вопросы")
            
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
                            'index': active_questions_index + len("## 7. Активные вопросы")
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
        """Получает содержимое базы знаний из Google Docs."""
        try:
            logger.info(f"Получаем документ {self.knowledge_base_doc_id}")
            
            # Получаем документ
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            if not content:
                logger.error("Документ пустой")
                return ""
                
            logger.info(f"Получен документ с {len(content)} элементами")
            
            # Извлекаем текст
            full_text = []
            for element in content:
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        if text := part.get('textRun', {}).get('content'):
                            full_text.append(text)
                            
            result = ''.join(full_text)
            logger.info(f"Извлечено {len(result)} символов текста")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get knowledge base: {e}")
            return ""

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

    async def get_section_content(self, topic: str) -> Optional[str]:
        """Получает содержимое конкретного раздела"""
        try:
            # Маппинг тем на заголовки разделов
            topic_headers = {
                'адрес': '## 1. Основная информация',
                'время': '## 1. Основная информация',
                'контакты': '## 1. Основная информация',
                'акции': '## 2. Текущие акции',
                'программа': '## 3. Программа лояльности',
                'корпоративным': '## 4. Корпоративным клиентам',
                'вопросы': '## 6. FAQ'
            }
            
            logger.info(f"Ищем раздел для темы: {topic}")
            
            if topic not in topic_headers:
                logger.warning(f"Тема '{topic}' не найдена в маппинге")
                return None
                
            # Возвращаем нужную секцию
            header = topic_headers[topic]
            section_content = self.sections.get(header)
            
            if section_content:
                logger.info(f"Найден контент для раздела '{header}' ({len(section_content)} символов)")
            else:
                logger.warning(f"Не найден контент для раздела '{header}'")
                
            return section_content
            
        except Exception as e:
            logger.error(f"Error getting section content: {e}")
            return None

    async def update_section(self, section_title: str, new_content: str):
        """Обновление содержимого раздела."""
        try:
            # Находим индекс раздела
            section_index = self._find_section_index(self.service.documents().get(documentId=self.knowledge_base_doc_id).execute(), section_title)
            
            if section_index == -1:
                logger.error(f"Section {section_title} not found")
                return
            
            # Находим конец раздела
            content = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute().get('body', {}).get('content', [])
            next_section_start = -1
            current_index = 1
            
            for element in content:
                if 'paragraph' in element:
                    for part in element['paragraph'].get('elements', []):
                        text = part.get('textRun', {}).get('content', '')
                        if current_index > section_index and text.strip().startswith('#'):
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
                            'startIndex': section_index + len(section_title) + 1,
                            'endIndex': next_section_start
                        }
                    }
                })
            
            # Добавляем новый контент
            requests.append({
                'insertText': {
                    'location': {
                        'index': section_index + len(section_title) + 1
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

    async def create_knowledge_base_doc(self) -> str:
        """Создание нового документа базы знаний и сохранение его ID."""
        try:
            # Создаем новый документ
            doc = self.service.documents().create(body={
                'title': 'База знаний Cvety.kz'
            }).execute()
            
            # Получаем ID нового документа
            doc_id = doc.get('documentId')
            
            # Настраиваем права доступа
            drive_service = build('drive', 'v3', credentials=self.service._http.credentials)
            
            # Открываем доступ для всех на чтение
            drive_service.permissions().create(
                fileId=doc_id,
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
            
            # Открываем доступ на редактирование для alekenov@gmail.com
            drive_service.permissions().create(
                fileId=doc_id,
                body={'type': 'user', 'role': 'writer', 'emailAddress': 'alekenov@gmail.com'},
                fields='id'
            ).execute()
            
            # Сохраняем ID в базу данных
            conn = psycopg2.connect(
                host=SUPABASE_CONFIG['host'],
                port=SUPABASE_CONFIG['port'],
                user=SUPABASE_CONFIG['user'],
                password=SUPABASE_CONFIG['password'],
                database=SUPABASE_CONFIG['database']
            )
            conn.autocommit = True
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO credentials (service_name, credential_key, credential_value)
                    VALUES ('google', 'docs_knowledge_base_id', %s)
                    ON CONFLICT (service_name, credential_key) DO UPDATE SET credential_value = %s
                    """,
                    (doc_id, doc_id)
                )
            
            # Обновляем ID в текущем экземпляре
            self.knowledge_base_doc_id = doc_id
            
            # Создаем начальную структуру
            await self.create_initial_structure()
            
            logger.info(f"Successfully created new knowledge base document with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to create knowledge base document: {e}")
            raise

    async def get_relevant_knowledge(self, query: str) -> str:
        """Получение релевантных частей базы знаний на основе запроса."""
        try:
            # Получаем документ
            doc = self.service.documents().get(documentId=self.knowledge_base_doc_id).execute()
            content = doc.get('body', {}).get('content', [])
            
            if not content:
                return "Извините, база знаний пуста или недоступна"
            
            # Разбиваем документ на секции
            sections = []
            current_section = {
                "title": "Начало документа",
                "content": "",
                "level": 0,
                "path": ["База знаний"]
            }
            section_path = []
            
            for element in content:
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    text = ""
                    for part in paragraph.get('elements', []):
                        if 'textRun' in part:
                            text += part['textRun'].get('content', '')
                    
                    # Проверяем, является ли текст заголовком
                    if text.strip().startswith('#'):
                        if current_section["content"]:
                            sections.append(current_section.copy())
                        
                        # Определяем уровень заголовка по количеству #
                        level = len(text.split()[0])
                        
                        # Обновляем путь секции
                        while section_path and section_path[-1]["level"] >= level:
                            section_path.pop()
                        section_path.append({"title": text.strip(), "level": level})
                        
                        current_section = {
                            "title": text.strip(), 
                            "content": "", 
                            "level": level,
                            "path": [p["title"] for p in section_path]
                        }
                    else:
                        current_section["content"] += text

            # Добавляем последнюю секцию
            if current_section["content"]:
                sections.append(current_section)
            
            # Словарь категорий и связанных слов
            categories = {
                "контакты": {
                    "keywords": ["контакт", "связь", "позвонить", "написать", "адрес", "контакты", "где", "найти", "whatsapp"],
                    "related": ["телефон", "whatsapp", "адрес", "instagram", "почта", "расположен", "находится"]
                },
                "время_работы": {
                    "keywords": ["время", "часы", "работаете", "открыты", "график", "режим"],
                    "related": ["режим", "выходные", "перерыв", "закрыты", "доставка"]
                },
                "доставка": {
                    "keywords": ["доставка", "привезти", "доставить", "привоз", "курьер", "самовывоз"],
                    "related": ["курьер", "самовывоз", "время", "зона", "бесплатно"]
                }
            }
            
            # Подготовка запроса
            query = query.lower()
            query_words = set(query.split())
            
            # Определяем категорию запроса
            query_category = None
            max_matches = 0
            
            for category, words in categories.items():
                # Считаем совпадения с ключевыми словами (вес 2) и связанными словами (вес 1)
                matches = sum(2 for word in query_words if any(kw in word or word in kw for kw in words["keywords"]))
                matches += sum(1 for word in query_words if any(rw in word or word in rw for rw in words["related"]))
                
                if matches > max_matches:
                    max_matches = matches
                    query_category = category
            
            # Оценка релевантности
            relevant_sections = []
            for section in sections:
                # Пропускаем секции с примерами диалогов и служебные разделы
                skip_keywords = ['пример', 'диалог', 'тест', 'обучение', 'вопрос']
                if any(kw in " ".join(section["path"]).lower() for kw in skip_keywords):
                    continue
                
                # Очищаем текст от лишних символов и форматирования
                title = section["title"].strip('# ').strip()
                content = section["content"].strip()
                
                # Объединяем заголовок и содержимое для поиска
                section_text = (title + " " + content).lower()
                
                # Считаем релевантность по нескольким факторам
                relevance_score = 0
                
                # 1. Прямые совпадения слов запроса (вес 4)
                query_matches = sum(4 for word in query_words if word in section_text)
                relevance_score += query_matches
                
                # 2. Частичные совпадения (вес 2)
                partial_matches = sum(2 for word in query_words if any(word in text or text in word for text in section_text.split()))
                relevance_score += partial_matches
                
                # 3. Совпадение категории (если определена)
                if query_category:
                    max_category_matches = 0
                    section_category = None
                    
                    for category, words in categories.items():
                        # Считаем совпадения с ключевыми словами категории
                        category_matches = sum(1 for kw in words["keywords"] if any(kw in text or text in kw for text in section_text.split()))
                        if category_matches > max_category_matches:
                            max_category_matches = category_matches
                            section_category = category
                    
                    # Если категория секции совпадает с категорией запроса
                    if section_category == query_category:
                        relevance_score *= 1.5  # Увеличиваем релевантность на 50%
                
                if relevance_score > 2:  # Минимальный порог релевантности
                    relevant_sections.append((section, relevance_score))
            
            # Сортируем секции по релевантности
            relevant_sections.sort(key=lambda x: x[1], reverse=True)
            
            # Берем только самую релевантную секцию
            if relevant_sections:
                section = relevant_sections[0][0]
                content = section["content"].strip()
                content = content.replace('#', '').strip()
                
                # Очищаем путь от символов форматирования
                clean_path = []
                for p in section["path"][1:]:  # Пропускаем первый элемент (общий заголовок)
                    clean_p = p.strip('# ').strip()
                    if clean_p and not clean_p.startswith('База знаний'):
                        clean_path.append(clean_p)
                
                if clean_path:
                    response = f"{' > '.join(clean_path)}:\n\n"
                    response += '\n'.join(content.split('\n'))
                    return response.strip()
            
            return "Извините, я не нашел релевантной информации по вашему вопросу. Попробуйте переформулировать вопрос или уточните, что именно вас интересует."
            
        except Exception as e:
            logger.error(f"Error getting relevant knowledge: {e}")
            return "Произошла ошибка при поиске информации"

    async def get_response(self, query: str, inventory_data: list = None) -> str:
        """Получает ответ на запрос пользователя"""
        try:
            logger.info(f"Получен запрос: {query}")
            logger.info(f"Данные инвентаря:\n{inventory_data}")

            # Проверяем запрос на наличие ключевых слов о товарах
            product_keywords = ['цена', 'стоимость', 'сколько стоит', 'купить', 'заказать', 'есть ли в наличии', 'остаток', 'что есть']
            
            if any(keyword in query.lower() for keyword in product_keywords):
                # Если запрос общий о наличии
                general_keywords = ['что есть', 'покажи', 'какие есть', 'ассортимент', 'наличие']
                if any(keyword in query.lower() for keyword in general_keywords):
                    if not inventory_data:
                        return "Извините, информация о наличии цветов временно недоступна"
                    
                    response = "В наличии следующие цветы:\n\n"
                    for item in inventory_data:
                        response += f"🌸 {item['name']}: {item['price']}"
                        if item['quantity'] > 0:
                            response += f" (в наличии: {item['quantity']})"
                        if item['description']:
                            response += f"\n   {item['description']}"
                        response += "\n\n"
                    return response
                
                # Если запрос о конкретном товаре
                for item in inventory_data or []:
                    if item['name'].lower() in query.lower():
                        response = (
                            f"🌸 {item['name']}\n"
                            f"💰 Цена: {item['price']}\n"
                            f"📦 В наличии: {item['quantity']} шт."
                        )
                        if item['description']:
                            response += f"\n📝 Описание: {item['description']}"
                        return response
                
                return "Извините, я не нашел такой товар в нашем каталоге. Хотите посмотреть весь ассортимент?"
            
            # Если запрос не о товарах, ищем в базе знаний
            return await self.get_relevant_knowledge(query)
            
        except Exception as e:
            logger.error(f"Ошибка при получении ответа: {str(e)}", exc_info=True)
            return "Извините, произошла ошибка при обработке вашего вопроса. Попробуйте спросить по-другому или свяжитесь с оператором."

    def find_relevant_section(self, query: str) -> Optional[str]:
        """Находит релевантный раздел для запроса."""
        try:
            query = query.lower()
            best_match = None
            best_score = 0

            # Специальные случаи
            if any(word in query for word in ['адрес', 'где', 'находитесь', 'расположен']):
                for section, content in self.sections.items():
                    if '## 1. Основная информация' in section:
                        # Извлекаем только часть про адрес
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'адрес:' in line.lower():
                                return line.split(':', 1)[1].strip()
                        return content

            # WhatsApp
            if any(word in query for word in ['уатсап', 'ватсап', 'whatsapp', 'вацап', 'what', 'app', 'вотсап']):
                for section, content in self.sections.items():
                    if '## 1. Основная информация' in section:
                        # Извлекаем только часть про WhatsApp
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'whatsapp:' in line.lower():
                                return line.split(':', 1)[1].strip()
                        return content

            # Ищем во всех разделах
            for section, content in self.sections.items():
                score = 0
                
                # Проверяем заголовок
                section_lower = section.lower()
                for word in query.split():
                    if word in section_lower:
                        score += 2
                
                # Проверяем содержимое
                content_lower = content.lower()
                for word in query.split():
                    if word in content_lower:
                        score += 1
                
                if score > best_score:
                    best_score = score
                    best_match = content

            if best_score > 0:
                logger.info(f"Найден релевантный раздел (score: {best_score})")
                return best_match
            
            logger.info("Не найден релевантный раздел")
            return None

        except Exception as e:
            logger.error(f"Ошибка при поиске релевантного раздела: {e}")
            return None
