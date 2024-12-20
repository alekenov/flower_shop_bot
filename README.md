# Flower Shop Telegram Bot 

Telegram бот для цветочного магазина с интеграцией Google Sheets для управления инвентарем и использованием OpenAI для генерации ответов.

## Обзор проекта

Бот автоматизирует обработку частых вопросов клиентов цветочного магазина, отвечая на типичные вопросы о доставке, ценах и наличии цветов, а также собирает данные для улучшения сервиса.

### Цели проекта
1. Быстрые ответы на базовые вопросы через Telegram
2. Сбор и анализ вопросов клиентов для улучшения сервиса
3. Интеграция с базами данных для актуальной информации
4. Автоматизация работы с Instagram Direct

## Основной функционал

### Работа с клиентами
- Ответы на частые вопросы:
  - Цены на букеты
  - График работы
  - Условия доставки
  - Способы оплаты
- Поиск и предоставление информации о товарах
- Обработка специальных запросов
- Интеграция с Instagram Direct

### Интеграции
- **Google Sheets**
  - Синхронизация каталога товаров
  - Управление инвентарем
  - Обновление цен и наличия
- **OpenAI**
  - Генерация естественных ответов
  - Обработка сложных запросов
  - Поддержка контекста разговора
- **Supabase**
  - Хранение данных пользователей и учетных данных
  - Логирование взаимодействий
  - Кэширование ответов
- **Instagram**
  - Обработка сообщений из Instagram Direct
  - Автоматические ответы на типовые вопросы
  - Интеграция с общей системой обработки заказов

## Структура проекта

```
flower_shop_bot/
├── src/                      # Основной код проекта
│   ├── telegram_bot.py       # Основной файл бота
│   ├── services/            # Сервисные модули
│   │   ├── sheets_service.py   # Работа с Google Sheets
│   │   ├── supabase_service.py # Работа с базой данных
│   │   ├── config_service.py   # Управление конфигурацией
│   │   └── instagram_service.py # Работа с Instagram API
│   ├── instagram/           # Модули для работы с Instagram
│   │   ├── api.py          # Instagram Graph API клиент
│   │   └── messages.py     # Обработка сообщений
│   └── utils/              # Вспомогательные модули
│       └── logger.py       # Система логирования
├── supabase/               # Конфигурация Supabase
│   └── migrations/         # Миграции базы данных
├── docs/                   # Документация
│   ├── openai.md          # Документация по OpenAI
│   ├── instagram.md       # Документация по Instagram
│   └── roadmap.md         # План развития
└── requirements.txt        # Зависимости проекта
```

## Установка и настройка

### 1. Подготовка окружения

1. Клонируйте репозиторий:
   ```bash
   git clone [repository-url]
   cd flower_shop_bot
   ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Настройка учетных данных

Все учетные данные хранятся в таблице `credentials` в базе данных Supabase. Необходимо настроить следующие сервисы:

1. **Telegram Bot**
   ```sql
   INSERT INTO credentials (service_name, credential_key, credential_value, description)
   VALUES 
   ('telegram', 'bot_token_dev', 'your_token', 'Development bot token'),
   ('telegram', 'bot_token_prod', 'your_token', 'Production bot token');
   ```

2. **OpenAI API**
   ```sql
   INSERT INTO credentials (service_name, credential_key, credential_value, description)
   VALUES 
   ('openai', 'api_key', 'your_key', 'OpenAI API Key'),
   ('openai', 'model', 'gpt-4-1106-preview', 'OpenAI Model Name');
   ```

3. **Google Sheets**
   ```sql
   INSERT INTO credentials (service_name, credential_key, credential_value, description)
   VALUES 
   ('google', 'spreadsheet_id', 'your_id', 'Google Spreadsheet ID');
   ```

4. **Instagram**
   ```sql
   INSERT INTO credentials (service_name, credential_key, credential_value, description)
   VALUES 
   ('instagram', 'access_token', 'your_token', 'Instagram Graph API Token'),
   ('instagram', 'user_id', 'your_id', 'Instagram Business Account ID');
   ```

### 3. Запуск бота

```bash
cd src
python3 telegram_bot.py
```

## Мониторинг и обслуживание

### Логирование
- Все логи сохраняются в базу данных в таблицу `bot_logs`
- Критические ошибки отправляются в Telegram канал мониторинга
- Статистика использования доступна в таблице `usage_stats`

### Обновление учетных данных
1. Проверка текущих учетных данных:
   ```sql
   SELECT service_name, credential_key, updated_at 
   FROM credentials 
   ORDER BY service_name;
   ```

2. Обновление учетных данных:
   ```sql
   UPDATE credentials 
   SET credential_value = 'new_value', 
       updated_at = CURRENT_TIMESTAMP
   WHERE service_name = 'service' 
   AND credential_key = 'key';
   ```

## План развития

Текущий план развития проекта доступен в [docs/roadmap.md](docs/roadmap.md).

## Лицензия

MIT License. См. файл LICENSE для деталей.
