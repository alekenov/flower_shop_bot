-- Create the message_logs table
CREATE TABLE IF NOT EXISTS message_logs (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT,
    user_name TEXT,
    message_text TEXT NOT NULL,
    message_type TEXT NOT NULL, -- 'command', 'text', 'callback'
    response_text TEXT,
    response_type TEXT, -- 'command_response', 'ai_response', 'error'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processing_time DOUBLE PRECISION, -- в миллисекундах
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_message_logs_chat_id ON message_logs(chat_id);
CREATE INDEX IF NOT EXISTS idx_message_logs_created_at ON message_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_message_logs_user_id ON message_logs(user_id);

-- Add RLS policies
ALTER TABLE message_logs ENABLE ROW LEVEL SECURITY;

-- Allow the service role to do everything
CREATE POLICY "Service role can do everything on message_logs"
    ON message_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
