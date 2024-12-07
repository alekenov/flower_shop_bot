# PRD: Система улучшения бота Cvety.kz

## Обзор
Простая система для улучшения качества ответов бота, основанная на Google Docs. Система позволяет отслеживать вопросы без ответов и пополнять базу знаний бота.

## Документы
Система использует два Google Docs документа:

### 1. Документ "Неотвеченные вопросы"
Автоматически пополняемый документ со списком вопросов, на которые бот не смог дать ответ.

**Формат записи:**
```
[Дата и время] 12.12.2024 15:30
[Вопрос] Как добавить новый способ оплаты?
[Контекст] 
- Пользователь: Хочу добавить новую карту
- Бот: Какую карту вы хотите добавить?
- Пользователь: Как добавить новый способ оплаты?
[Статус] ❌ Не отвечено

---
```

### 2. Документ "База знаний"
Структурированный документ с ответами на вопросы.

**Структура документа:**
```markdown
# 1. Заказы и оплата
## 1.1 Создание заказа
В: Как создать новый заказ?
О: Нажмите на кнопку "+" в нижней части экрана. Выберите тип букета и заполните информацию о заказе.

## 1.2 Оплата
В: Как добавить новый способ оплаты?
О: Перейдите в раздел "Настройки" → "Способы оплаты" → нажмите "+" → выберите тип карты и введите данные.

# 2. Доставка
...

# 3. Товары и цены
...
```

## Процесс работы

### Пополнение базы неотвеченных вопросов
1. Бот не находит ответ на вопрос
2. Отправляет пользователю сообщение: "Извините, я пока не знаю ответ на этот вопрос. Я передам его нашим специалистам."
3. Автоматически добавляет запись в документ "Неотвеченные вопросы"

### Обработка вопросов
1. Ежедневный просмотр документа "Неотвеченные вопросы"
2. Подготовка ответов на частые вопросы
3. Добавление ответов в "Базу знаний"
4. Обновление статуса вопросов на ✅ Отвечено

### Обновление бота
1. Раз в неделю (пятница) обновление базы знаний бота
2. После обновления - тестирование новых ответов

## Правила составления ответов

### Требования к ответам:
- Простой язык без технических терминов
- Короткие предложения
- Пошаговые инструкции
- Конкретные действия ("нажмите", "выберите", "введите")

### Пример хорошего ответа:
```
В: Как отменить заказ?
О: 
1. Откройте заказ
2. Нажмите красную кнопку "Отменить" внизу экрана
3. Выберите причину отмены
4. Нажмите "Подтвердить"

Деньги вернутся на карту через 3-5 дней.
```

### Пример плохого ответа:
```
В: Как отменить заказ?
О: Для отмены заказа необходимо произвести ряд действий в интерфейсе, включая выбор соответствующей опции в меню и подтверждение операции.
```

## Метрики
- Количество неотвеченных вопросов в неделю
- Время от появления вопроса до добавления ответа
- % повторяющихся вопросов
- Удовлетворенность пользователей ответами бота

## Ответственные
- Просмотр неотвеченных вопросов: ежедневно, утро
- Добавление ответов: по мере поступления вопросов
- Обновление бота: пятница, 10:00

## Дальнейшие улучшения
1. Автоматическое оповещение о новых вопросах
2. Категоризация частых вопросов
3. Автоматическое обновление базы знаний бота