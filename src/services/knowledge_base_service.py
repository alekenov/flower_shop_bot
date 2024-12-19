import logging
import re
from typing import Dict, List, Set, Tuple
from datetime import datetime
from collections import defaultdict
import asyncio
from src.services.docs_service import DocsService

logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    def __init__(self):
        self.docs_service = DocsService()
        self.knowledge_cache = {}
        self.last_update = None
        self.cache_ttl = 3600  # 1 час
        
        # Теги и их синонимы
        self.tag_synonyms = {
            'цены': {'стоимость', 'прайс', 'сколько стоит', 'стоит'},
            'доставка': {'привезти', 'доставить', 'курьер', 'самовывоз'},
            'розы': {'роза', 'розочка', 'розочки', 'розами'},
            'букеты': {'букет', 'композиция', 'композиции', 'аранжировка'},
            'оплата': {'оплатить', 'платеж', 'kaspi', 'каспи', 'карта'},
            'время_работы': {'режим', 'график', 'часы работы', 'когда работаете'},
            'контакты': {'телефон', 'почта', 'email', 'связаться'},
            'акции': {'скидка', 'скидки', 'распродажа', 'спецпредложение'},
        }
        
        # Веса для разных типов совпадений
        self.match_weights = {
            'exact': 1.0,    # Точное совпадение
            'synonym': 0.8,   # Совпадение синонима
            'partial': 0.6,   # Частичное совпадение
            'context': 0.4    # Контекстное совпадение
        }
        
        # Структура разделов и их приоритеты
        self.section_priorities = {
            '## 1. Основная информация': 1,
            '## 2. Каталог и цены': 1,
            '## 3. Доставка': 1,
            '## 4. Оплата': 1,
            '## 5. Специальные предложения': 0.8,
            '## 6. FAQ': 0.7
        }

    async def _update_cache_if_needed(self) -> None:
        """Обновляет кэш, если он устарел."""
        current_time = datetime.now().timestamp()
        if (not self.last_update or 
            current_time - self.last_update > self.cache_ttl):
            try:
                content = await self.docs_service.get_knowledge_base()
                self.knowledge_cache = self._parse_content(content)
                self.last_update = current_time
                logger.info("Knowledge base cache updated successfully")
            except Exception as e:
                logger.error(f"Failed to update knowledge base cache: {e}")
                if not self.knowledge_cache:
                    raise

    def _parse_content(self, content: str) -> Dict[str, Dict]:
        """Парсит контент базы знаний и создает структурированный кэш."""
        sections = {}
        current_section = None
        current_subsection = None
        current_text = []
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_section:
                    sections[current_section]['content'] = '\n'.join(current_text)
                current_section = line.strip()
                current_subsection = None
                current_text = []
                sections[current_section] = {
                    'subsections': {},
                    'content': '',
                    'tags': self._extract_tags(line)
                }
            elif line.startswith('### '):
                if current_subsection:
                    sections[current_section]['subsections'][current_subsection] = {
                        'content': '\n'.join(current_text),
                        'tags': self._extract_tags('\n'.join(current_text))
                    }
                current_subsection = line.strip()
                current_text = []
            else:
                current_text.append(line)
                
        # Добавляем последнюю секцию
        if current_section:
            if current_subsection:
                sections[current_section]['subsections'][current_subsection] = {
                    'content': '\n'.join(current_text),
                    'tags': self._extract_tags('\n'.join(current_text))
                }
            else:
                sections[current_section]['content'] = '\n'.join(current_text)
                
        return sections

    def _extract_tags(self, text: str) -> Set[str]:
        """Извлекает теги из текста на основе синонимов и контекста."""
        tags = set()
        text_lower = text.lower()
        
        # Проверяем прямые совпадения и синонимы
        for main_tag, synonyms in self.tag_synonyms.items():
            if main_tag in text_lower:
                tags.add(main_tag)
            for synonym in synonyms:
                if synonym in text_lower:
                    tags.add(main_tag)
                    
        # Добавляем контекстные теги
        if any(word in text_lower for word in ['тг', 'тенге', '₸']):
            tags.add('цены')
        if any(word in text_lower for word in ['часы', 'время', 'график']):
            tags.add('время_работы')
        if any(word in text_lower for word in ['акция', '%', 'скидка']):
            tags.add('акции')
            
        return tags

    async def find_relevant_content(self, query: str, max_results: int = 3) -> List[Tuple[str, float]]:
        """Находит релевантный контент на основе запроса."""
        await self._update_cache_if_needed()
        
        query_lower = query.lower()
        query_tags = self._extract_tags(query)
        results = []
        
        for section, data in self.knowledge_cache.items():
            # Вычисляем релевантность секции
            section_score = self._calculate_relevance(
                query_lower,
                section + '\n' + data['content'],
                query_tags,
                data['tags'],
                self.section_priorities.get(section, 0.5)
            )
            
            if section_score > 0:
                results.append((section + '\n' + data['content'], section_score))
            
            # Проверяем подсекции
            for subsection, subdata in data['subsections'].items():
                subsection_score = self._calculate_relevance(
                    query_lower,
                    subsection + '\n' + subdata['content'],
                    query_tags,
                    subdata['tags'],
                    self.section_priorities.get(section, 0.5) * 0.9
                )
                
                if subsection_score > 0:
                    results.append((
                        f"{section}\n{subsection}\n{subdata['content']}",
                        subsection_score
                    ))
        
        # Сортируем результаты по релевантности
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]

    def _calculate_relevance(self, query: str, content: str, 
                           query_tags: Set[str], content_tags: Set[str],
                           base_priority: float) -> float:
        """Вычисляет релевантность контента для запроса."""
        score = 0.0
        
        # Проверяем точные совпадения
        if query in content.lower():
            score += self.match_weights['exact']
            
        # Проверяем совпадения тегов
        common_tags = query_tags.intersection(content_tags)
        if common_tags:
            score += len(common_tags) * self.match_weights['synonym']
            
        # Проверяем частичные совпадения
        query_words = set(query.split())
        content_words = set(content.lower().split())
        common_words = query_words.intersection(content_words)
        if common_words:
            score += len(common_words) / len(query_words) * self.match_weights['partial']
            
        # Применяем приоритет секции
        score *= base_priority
        
        return score

    async def get_section_content(self, section_title: str) -> str:
        """Получает содержимое конкретной секции."""
        await self._update_cache_if_needed()
        
        if section_title in self.knowledge_cache:
            section_data = self.knowledge_cache[section_title]
            return section_data['content']
            
        # Ищем в подсекциях
        for section_data in self.knowledge_cache.values():
            if section_title in section_data['subsections']:
                return section_data['subsections'][section_title]['content']
                
        return ""
