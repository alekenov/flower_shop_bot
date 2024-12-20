# Управление учетными данными

## Обзор

Все учетные данные проекта хранятся в таблице `credentials` в базе данных Supabase. Это обеспечивает:
- Централизованное хранение всех учетных данных
- Безопасное управление доступом
- Возможность аудита изменений
- Простое обновление учетных данных

## Структура таблицы credentials

```sql
CREATE TABLE credentials (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    credential_key VARCHAR(100) NOT NULL,
    credential_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service_name, credential_key)
);
```

### Поля таблицы:
- `service_name`: Название сервиса (например, 'telegram', 'openai')
- `credential_key`: Ключ учетных данных (например, 'api_key', 'bot_token')
- `credential_value`: Значение учетных данных
- `description`: Описание для чего используются учетные данные
- `created_at`: Дата создания записи
- `updated_at`: Дата последнего обновления

## Сервисы и их учетные данные

### Telegram
```sql
-- Токен бота для разработки
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('telegram', 'bot_token_dev', 'your_token', 'Development bot token');

-- Токен бота для продакшена
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('telegram', 'bot_token_prod', 'your_token', 'Production bot token');
```

### OpenAI
```sql
-- API ключ
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('openai', 'api_key', 'your_key', 'OpenAI API Key');

-- Модель
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('openai', 'model', 'gpt-4-1106-preview', 'OpenAI Model Name');
```

### Google Sheets
```sql
-- ID таблицы
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('google', 'spreadsheet_id', 'your_id', 'Google Spreadsheet ID');

-- Учетные данные сервисного аккаунта
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('google', 'service_account', '{"type": "service_account", ...}', 'Google Service Account');
```

### Instagram
```sql
-- Токен доступа
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('instagram', 'access_token', 'your_token', 'Instagram Graph API Token');

-- ID бизнес-аккаунта
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES ('instagram', 'user_id', 'your_id', 'Instagram Business Account ID');
```

## Работа с учетными данными

### Получение учетных данных
```python
from services.config_service import config_service

# Получение значения
value = config_service.get_config('SERVICE_KEY')

# Получение значения с проверкой
value = config_service.get_config('SERVICE_KEY', required=True)
```

### Обновление учетных данных
```python
from services.config_service import config_service

# Обновление значения
success = config_service.set_config(
    'SERVICE_KEY',
    'new_value',
    'Description of the credential'
)
```

### Инвалидация кэша
```python
from services.config_service import config_service

# Инвалидация кэша для конкретного сервиса
config_service.invalidate_cache('service_name')

# Инвалидация всего кэша
config_service.invalidate_cache()
```

## Мониторинг и аудит

### Проверка устаревших учетных данных
```sql
SELECT service_name, credential_key, updated_at
FROM credentials
WHERE updated_at < NOW() - INTERVAL '30 days'
ORDER BY updated_at;
```

### Аудит изменений
```sql
SELECT service_name, credential_key, updated_at, created_at
FROM credentials
WHERE updated_at != created_at
ORDER BY updated_at DESC;
```

## Безопасность

1. **Доступ к базе данных**
   - Используйте минимально необходимые права доступа
   - Регулярно меняйте пароли доступа к базе данных
   - Используйте SSL для подключения

2. **Значения учетных данных**
   - Не используйте учетные данные напрямую в коде
   - Регулярно обновляйте токены и ключи
   - Используйте разные учетные данные для разработки и продакшена

3. **Мониторинг**
   - Отслеживайте все изменения учетных данных
   - Настройте оповещения при подозрительной активности
   - Регулярно проверяйте журналы доступа
