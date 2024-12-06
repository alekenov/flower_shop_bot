# Flower Shop Telegram Bot

Telegram бот для автоматизации обработки запросов клиентов цветочного магазина.

## Установка

1. Клонируйте репозиторий
2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `.env.example` и заполните необходимые переменные окружения

5. Запустите бота:
```bash
python src/main.py
```

## Структура проекта

```
flower_shop_bot/
├── config/         # Конфигурационные файлы
├── src/            # Исходный код
│   ├── bot/        # Обработчики команд и клавиатуры
│   ├── services/   # Сервисы (OpenAI, Google Sheets)
│   └── utils/      # Вспомогательные функции
└── tests/          # Тесты
```
