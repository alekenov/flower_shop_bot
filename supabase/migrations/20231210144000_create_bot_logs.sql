-- Create the bot_logs table
CREATE TABLE IF NOT EXISTS bot_logs (
    id BIGSERIAL PRIMARY KEY,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    user_id BIGINT,
    chat_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bot_logs_level ON bot_logs(level);
CREATE INDEX IF NOT EXISTS idx_bot_logs_category ON bot_logs(category);
CREATE INDEX IF NOT EXISTS idx_bot_logs_created_at ON bot_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_bot_logs_user_id ON bot_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_logs_chat_id ON bot_logs(chat_id);

-- Create the bot_metrics table
CREATE TABLE IF NOT EXISTS bot_metrics (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    tags JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bot_metrics_name ON bot_metrics(name);
CREATE INDEX IF NOT EXISTS idx_bot_metrics_timestamp ON bot_metrics(timestamp);

-- Add RLS policies
ALTER TABLE bot_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_metrics ENABLE ROW LEVEL SECURITY;

-- Allow the service role to do everything on bot_logs
CREATE POLICY "Service role can do everything on bot_logs"
    ON bot_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Allow the service role to do everything on bot_metrics
CREATE POLICY "Service role can do everything on bot_metrics"
    ON bot_metrics
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
