-- Add OpenAI credentials
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES 
    ('openai', 'api_key', '${OPENAI_API_KEY}', 'API ключ для доступа к OpenAI API'),
    ('openai', 'organization', '${OPENAI_ORG_ID}', 'ID организации в OpenAI')
ON CONFLICT (service_name, credential_key) 
DO UPDATE SET 
    credential_value = EXCLUDED.credential_value,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;
