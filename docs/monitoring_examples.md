# Примеры мониторинга OpenAI в цветочном магазине

## 1. Отслеживание использования токенов

### Пример дневной статистики:
```json
{
    "date": "2024-12-19",
    "total_tokens": 25430,
    "cost_usd": 0.51,
    "breakdown": {
        "prompt_tokens": 15200,
        "completion_tokens": 10230,
        "by_scenario": {
            "availability": 8500,
            "order": 12300,
            "faq": 4630
        }
    },
    "average_per_request": {
        "prompt": 76,
        "completion": 51
    }
}
```

### Пример почасовой нагрузки:
```json
{
    "hour": "11:00",
    "requests": 42,
    "tokens_used": 5460,
    "peak_tokens_per_minute": 240
}
```

## 2. Мониторинг качества ответов

### Пример оценки ответа:
```json
{
    "message_id": "msg_123",
    "scenario": "order",
    "metrics": {
        "response_relevance": 0.95,  // Насколько ответ соответствует вопросу
        "format_compliance": 1.0,    // Соответствие формату ответа
        "emotional_match": 0.85      // Соответствие эмоциональному контексту
    },
    "flags": {
        "missing_price": false,
        "incorrect_format": false,
        "inappropriate_tone": false
    },
    "user_feedback": {
        "rating": 5,                 // Оценка пользователя
        "completed_order": true      // Привел ли диалог к заказу
    }
}
```

### Пример агрегированной статистики качества:
```json
{
    "period": "2024-12-19",
    "total_conversations": 156,
    "success_metrics": {
        "order_completion_rate": 0.78,    // 78% заказов успешно оформлены
        "question_resolution_rate": 0.92,  // 92% вопросов получили удовлетворительный ответ
        "average_user_rating": 4.7         // Средняя оценка пользователей
    },
    "error_rates": {
        "misunderstanding_rate": 0.05,     // 5% ответов не по теме
        "format_error_rate": 0.02,         // 2% ответов с неправильным форматом
        "emotional_mismatch_rate": 0.03    // 3% ответов с неправильным тоном
    }
}
```

## 3. Статистика по типам запросов

### Пример почасовой статистики:
```json
{
    "hour": "11:00",
    "total_requests": 42,
    "by_type": {
        "availability": {
            "count": 18,
            "success_rate": 0.94,
            "avg_tokens": 120,
            "popular_items": ["розы", "тюльпаны", "лилии"]
        },
        "order": {
            "count": 15,
            "success_rate": 0.87,
            "avg_tokens": 180,
            "completion_rate": 0.73
        },
        "faq": {
            "count": 9,
            "success_rate": 0.98,
            "avg_tokens": 90,
            "top_questions": ["время работы", "доставка"]
        }
    },
    "user_satisfaction": {
        "positive_feedback": 38,
        "negative_feedback": 4
    }
}
```

### Пример анализа трендов:
```json
{
    "period": "неделя",
    "trends": {
        "growing_demand": ["розовые розы", "пионы"],
        "declining_demand": ["гвоздики"],
        "common_issues": ["цена доставки", "время работы"],
        "successful_patterns": {
            "time_to_order": "3-4 сообщения",
            "best_conversion": "после фото букета",
            "optimal_price_range": "5000-7000 тг"
        }
    }
}
```

## Использование статистики:

1. **Оптимизация токенов:**
   - Выявление "дорогих" диалогов
   - Корректировка промптов
   - Настройка сжатия контекста

2. **Улучшение качества:**
   - Обновление базы знаний по частым вопросам
   - Настройка эмоциональных ответов
   - Оптимизация сценариев заказа

3. **Бизнес-аналитика:**
   - Популярные товары и вопросы
   - Пиковые часы нагрузки
   - Эффективность конверсии
