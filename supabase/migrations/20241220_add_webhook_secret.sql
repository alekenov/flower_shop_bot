-- Добавляем секретный токен для вебхука в таблицу credentials
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES 
    ('telegram', 'webhook_secret', uuid_generate_v4(), 'Secret token for securing webhook endpoint')
ON CONFLICT (service_name, credential_key) 
DO UPDATE SET 
    credential_value = EXCLUDED.credential_value,
    description = EXCLUDED.description;
