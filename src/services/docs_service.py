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

            # Получаем учетные данные Google
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    """
                    SELECT credential_value 
                    FROM credentials 
                    WHERE service_name = 'google' AND credential_key = 'service_account'
                    """
                )
                result = cur.fetchone()
                if not result:
                    raise ValueError("Google service account credentials not found")
                credentials_info = json.loads(result['credential_value'])

            # Используем константу вместо запроса к БД
            self.knowledge_base_doc_id = KNOWLEDGE_BASE_DOC_ID

            # Создаем сервис Google Docs
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=[
                    'https://www.googleapis.com/auth/documents',
                    'https://www.googleapis.com/auth/drive.file'
                ]
            )
            self.service = build('docs', 'v1', credentials=credentials)
            logger.info("Successfully initialized Google Docs service")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs service: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

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
            
            # Разбиваем документ на секции по заголовкам
            sections = []
            current_section = {"title": "", "content": "", "level": 0, "path": []}
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
                "акции": {
                    "keywords": ["акция", "акции", "скидка", "скидки", "предложение", "специальное", "текущие", "действуют"],
                    "related": ["бесплатно", "процент", "выгода", "дешевле", "новый", "клиент", "первый"]
                },
                "программа_лояльности": {
                    "keywords": ["программа", "лояльность", "баллы", "бонусы", "накопить", "накопление", "программе"],
                    "related": ["скидка", "vip", "клиент", "постоянный", "использовать", "потратить"]
                },
                "корпоративные": {
                    "keywords": ["корпоратив", "компания", "фирма", "бизнес", "юридическое", "корпоративный"],
                    "related": ["документы", "отсрочка", "безнал", "счет", "договор", "менеджер"]
                },
                "контакты": {
                    "keywords": ["контакт", "связь", "позвонить", "написать", "адрес", "контакты"],
                    "related": ["телефон", "whatsapp", "адрес", "instagram", "почта"]
                },
                "время_работы": {
                    "keywords": ["время", "часы", "работаете", "открыты", "график", "режим"],
                    "related": ["режим", "выходные", "перерыв", "закрыты", "доставка"]
                },
                "оплата": {
                    "keywords": ["оплата", "платить", "оплатить", "деньги", "kaspi", "каспи"],
                    "related": ["наличные", "перевод", "счет", "карта", "терминал"]
                },
                "доставка": {
                    "keywords": ["доставка", "привезти", "доставить", "привоз", "курьер"],
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
                query_matches = sum(1 for word in query_words if any(word in text or text in word for text in section_text.split()))
                relevance_score += query_matches * 4
                
                # 2. Совпадения в заголовке имеют больший вес (вес 6)
                title_matches = sum(1 for word in query_words if any(word in text or text in word for text in title.lower().split()))
                relevance_score += title_matches * 6
                
                # 3. Совпадения по категории
                if query_category:
                    # Проверяем, соответствует ли секция категории запроса
                    section_category = None
                    max_category_matches = 0
                    
                    for category, words in categories.items():
                        # Считаем совпадения с ключевыми словами категории
                        category_matches = sum(1 for kw in words["keywords"] if any(kw in text or text in kw for text in section_text.split()))
                        if category_matches > max_category_matches:
                            max_category_matches = category_matches
                            section_category = category
                    
                    # Если категория секции совпадает с категорией запроса
                    if section_category == query_category:
                        relevance_score *= 1.5  # Увеличиваем релевантность на 50%
                        
                        # Дополнительные совпадения по ключевым словам (вес 3)
                        category_keywords = categories[query_category]["keywords"]
                        keyword_matches = sum(1 for kw in category_keywords if any(kw in text or text in kw for text in section_text.split()))
                        relevance_score += keyword_matches * 3
                        
                        # Связанные слова категории (вес 1)
                        related_words = categories[query_category]["related"]
                        related_matches = sum(1 for rw in related_words if any(rw in text or text in rw for text in section_text.split()))
                        relevance_score += related_matches
                
                # 4. Штраф за длинные секции
                words_count = len(section_text.split())
                if words_count > 50:  # Если секция длиннее 50 слов
                    length_penalty = (words_count - 50) / 100
                    relevance_score = relevance_score / (1 + length_penalty)
                
                # 5. Бонус за короткие, но информативные секции
                if words_count <= 50 and query_matches > 0:
                    relevance_score *= 1.2
                
                # 6. Штраф за слишком общие секции
                if len(section["path"]) <= 2:  # Если секция находится на верхнем уровне
                    relevance_score *= 0.8
                
                # 7. Бонус за точное совпадение с запросом
                if any(word.lower() == query.lower() for word in title.split()):
                    relevance_score *= 1.5
                
                # 8. Бонус за релевантный путь
                path_text = " ".join(section["path"]).lower()
                path_matches = sum(1 for word in query_words if any(word in text or text in word for text in path_text.split()))
                if path_matches > 0:
                    relevance_score *= (1 + path_matches * 0.2)  # Увеличиваем на 20% за каждое совпадение
                
                if relevance_score > 2:  # Минимальный порог релевантности
                    relevant_sections.append((section, relevance_score))
            
            # Сортируем секции по релевантности
            relevant_sections.sort(key=lambda x: x[1], reverse=True)
            
            # Формируем ответ из наиболее релевантных секций
            if relevant_sections:
                # Берем топ-2 наиболее релевантные секции
                response_sections = []
                used_content = set()  # Для отслеживания уникального контента
                
                # Выбираем уникальные секции
                for section, score in relevant_sections:
                    # Очищаем содержимое от лишних символов
                    content = section["content"].strip()
                    content = content.replace('#', '').strip()
                    
                    # Очищаем и форматируем каждую строку
                    clean_lines = []
                    for line in content.split('\n'):
                        line = line.strip()
                        # Пропускаем пустые строки и дубликаты
                        if line and not any(line in used_line or used_line in line for used_line in used_content):
                            clean_lines.append(line)
                            used_content.add(line)
                    
                    # Если есть уникальные строки
                    if clean_lines:
                        # Очищаем путь от символов форматирования
                        clean_path = []
                        for p in section["path"][1:]:  # Пропускаем первый элемент (общий заголовок)
                            clean_p = p.strip('# ').strip()
                            if clean_p and not clean_p.startswith('База знаний'):
                                clean_path.append(clean_p)
                        
                        if clean_path:
                            response_sections.append({
                                'path': " > ".join(clean_path),
                                'content': '\n'.join(clean_lines)
                            })
                        
                        if len(response_sections) >= 2:
                            break
                
                # Формируем финальный ответ
                if response_sections:
                    response = []
                    for section in response_sections:
                        response.append(f"{section['path']}:\n")
                        response.append(section['content'])
                    return '\n\n'.join(response).strip()
                else:
                    return "Извините, я не нашел релевантной информации по вашему вопросу. Попробуйте переформулировать вопрос или уточнить, что именно вас интересует."
            else:
                return "Извините, я не нашел релевантной информации по вашему вопросу. Попробуйте переформулировать вопрос или уточнить, что именно вас интересует."
            
        except Exception as e:
            logger.error(f"Error getting relevant knowledge: {e}")
            return "Произошла ошибка при поиске информации"
