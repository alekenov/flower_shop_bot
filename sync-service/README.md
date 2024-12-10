# Sync Service

Сервис для синхронизации данных между Google Sheets и Supabase с интервалом в 1 минуту.

## Настройка

1. Создайте файл `.env` в корне проекта:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
GOOGLE_CREDENTIALS={"type": "service_account", ...}
```

2. Установите зависимости:
```bash
npm install
```

3. Соберите TypeScript:
```bash
npm run build
```

## Запуск

### Локально
```bash
npm run start:sync
```

### Docker
```bash
# Сборка образа
docker build -t flower-shop-sync -f sync-service/Dockerfile .

# Запуск контейнера
docker run -d \
  --name flower-shop-sync \
  --env-file .env \
  flower-shop-sync
```

## Логи

Сервис выводит логи о каждой синхронизации, включая:
- Время начала синхронизации
- Количество добавленных товаров
- Количество обновленных товаров
- Количество удаленных товаров
- Ошибки, если они возникли

## Мониторинг

Вы можете следить за логами контейнера:
```bash
docker logs -f flower-shop-sync
```
