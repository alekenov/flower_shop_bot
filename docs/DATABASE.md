# База данных

## Подключение

Есть два способа настройки подключения к базе данных:

### 1. Через Supabase Dashboard (рекомендуемый способ)

1. Войдите в [Supabase Dashboard](https://supabase.com/dashboard)
2. Выберите ваш проект
3. Перейдите в раздел "Settings" -> "Database"
4. В секции "Connection Info" вы найдете:
   - Host: `[project-ref].supabase.co`
   - Database name: `postgres`
   - Port: `5432`
   - User: `postgres`
   - Password: `[ваш-пароль]`

Эти данные нужно сохранить в таблице `credentials` с service_name='supabase':
```sql
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES 
  ('supabase', 'db_host', 'your-project-ref.supabase.co', 'Supabase database host'),
  ('supabase', 'db_name', 'postgres', 'Supabase database name'),
  ('supabase', 'db_port', '5432', 'Supabase database port'),
  ('supabase', 'db_user', 'postgres', 'Supabase database user'),
  ('supabase', 'db_password', 'your-password', 'Supabase database password');
```

### 2. Через переменные окружения (для первоначальной настройки)

Для первого подключения, когда таблица `credentials` еще не создана, используйте переменные окружения:

```env
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_HOST=your-project-ref.supabase.co
SUPABASE_DB_PORT=5432
```

После успешного подключения и создания таблицы `credentials`, перенесите данные в неё, используя SQL запрос выше.

**Важно**: 
- Никогда не храните учетные данные в коде или в системе контроля версий
- После переноса данных в таблицу `credentials`, можно удалить переменные окружения
- Убедитесь, что файл `.env` добавлен в `.gitignore`

## Структура базы данных

### Основные таблицы

1. `products` - Каталог товаров
   - `id`: SERIAL PRIMARY KEY
   - `name`: VARCHAR(255) NOT NULL
   - `description`: TEXT
   - `price`: DECIMAL(10,2)
   - `category`: VARCHAR(100)
   - `image_url`: TEXT
   - `in_stock`: BOOLEAN DEFAULT true
   - `quantity`: INTEGER
   - `created_at`, `updated_at`: TIMESTAMP WITH TIME ZONE

2. `knowledge_base` - База знаний
   - `id`: SERIAL PRIMARY KEY
   - `title`: VARCHAR(255)
   - `content`: TEXT NOT NULL
   - `category`: VARCHAR(100)
   - `tags`: TEXT[]
   - `created_at`, `updated_at`: TIMESTAMP WITH TIME ZONE

3. `credentials` - Учетные данные
   - `id`: SERIAL PRIMARY KEY
   - `service_name`: VARCHAR(50) NOT NULL
   - `credential_key`: VARCHAR(100) NOT NULL
   - `credential_value`: TEXT NOT NULL
   - `description`: TEXT
   - `created_at`, `updated_at`: TIMESTAMP WITH TIME ZONE
   - UNIQUE(service_name, credential_key)

### Логи и кэш

4. `bot_logs` - Логи бота
   - `id`: SERIAL PRIMARY KEY
   - `level`: VARCHAR(50) NOT NULL
   - `category`: VARCHAR(50) NOT NULL
   - `message`: TEXT NOT NULL
   - `metadata`: JSONB
   - `user_id`: BIGINT
   - `chat_id`: BIGINT
   - `created_at`: TIMESTAMP WITH TIME ZONE

5. `ai_response_cache` - Кэш ответов AI
   - `id`: SERIAL PRIMARY KEY
   - `query_hash`: VARCHAR(64) NOT NULL UNIQUE
   - `query_text`: TEXT NOT NULL
   - `response_text`: TEXT NOT NULL
   - `hit_count`: INTEGER DEFAULT 1
   - `created_at`, `updated_at`: TIMESTAMP WITH TIME ZONE

### Пользовательские данные

6. `conversations` - История разговоров
   - `id`: BIGSERIAL PRIMARY KEY
   - `user_id`: BIGINT
   - `message`: TEXT NOT NULL
   - `response`: TEXT
   - `created_at`: TIMESTAMP WITH TIME ZONE

7. `user_preferences` - Настройки пользователей
   - `id`: SERIAL PRIMARY KEY
   - `user_id`: BIGINT NOT NULL UNIQUE
   - `settings`: JSONB
   - `created_at`, `updated_at`: TIMESTAMP WITH TIME ZONE

8. `user_insights` - Инсайты о пользователях
   - `id`: SERIAL PRIMARY KEY
   - `user_id`: BIGINT NOT NULL
   - `type`: VARCHAR(50) NOT NULL
   - `data`: JSONB NOT NULL
   - `created_at`: TIMESTAMP WITH TIME ZONE

9. `interaction_patterns` - Паттерны взаимодействия
   - `id`: SERIAL PRIMARY KEY
   - `user_id`: BIGINT NOT NULL
   - `type`: VARCHAR(50) NOT NULL
   - `data`: JSONB NOT NULL
   - `created_at`: TIMESTAMP WITH TIME ZONE

10. `bot_metrics` - Метрики бота
    - `id`: SERIAL PRIMARY KEY
    - `metric_name`: VARCHAR(50) NOT NULL
    - `metric_value`: JSONB NOT NULL
    - `created_at`: TIMESTAMP WITH TIME ZONE

## Миграции

Все миграции хранятся в двух директориях:
- `/migrations/` - для общих миграций
- `/supabase/migrations/` - для миграций Supabase

## Безопасность

1. Все чувствительные данные хранятся в таблице `credentials`
2. Пароли и ключи API никогда не хранятся в открытом виде
3. Для таблицы `message_logs` настроена Row Level Security (RLS)

## Обслуживание

1. Регулярно проверяйте размер таблиц логов
2. Настройте политику хранения для старых записей
3. Следите за производительностью индексов

## Подключение в коде

Для работы с базой данных используется единый `database_service`:

```python
from services.database_service import database_service

# Выполнение запроса с получением всех строк
results = database_service.execute_query(
    "SELECT * FROM table WHERE column = %s",
    (value,)
)

# Выполнение запроса с получением одной строки
result = database_service.execute_query_single(
    "SELECT * FROM table WHERE id = %s",
    (id,)
)

# Выполнение запроса без получения результата
database_service.execute_query(
    "INSERT INTO table (column) VALUES (%s)",
    (value,),
    fetch=False
)
