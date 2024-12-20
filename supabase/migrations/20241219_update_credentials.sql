-- Create credentials table if not exists
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    credential_key VARCHAR(100) NOT NULL,
    credential_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    UNIQUE(service_name, credential_key)
);

-- Create trigger for updating updated_at on credentials
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_credentials_updated_at'
    ) THEN
        CREATE TRIGGER update_credentials_updated_at
            BEFORE UPDATE ON credentials
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Create indexes for credentials
CREATE INDEX IF NOT EXISTS idx_credentials_service_name ON credentials(service_name);
CREATE INDEX IF NOT EXISTS idx_credentials_service_key ON credentials(service_name, credential_key);

-- Drop service_accounts table if exists (replaced by credentials)
DROP TABLE IF EXISTS service_accounts;

-- Add OpenAI credentials
INSERT INTO credentials (service_name, credential_key, credential_value, description)
VALUES 
    ('openai', 'api_key', 'sk-...your-key...', 'OpenAI API Key'),
    ('openai', 'model', 'gpt-4-1106-preview', 'OpenAI Model Name')
ON CONFLICT (service_name, credential_key) 
DO UPDATE SET 
    credential_value = EXCLUDED.credential_value,
    description = EXCLUDED.description;
