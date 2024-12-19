-- Создаем базовые таблицы
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    content TEXT NOT NULL,
    role VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Таблица для отслеживания использования токенов
CREATE TABLE IF NOT EXISTS token_usage (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(10,4) NOT NULL,
    scenario VARCHAR(50),
    message_id UUID REFERENCES messages(id)
);

-- Таблица для мониторинга качества ответов
CREATE TABLE IF NOT EXISTS response_quality (
    id SERIAL PRIMARY KEY,
    message_id UUID REFERENCES messages(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    scenario VARCHAR(50) NOT NULL,
    response_relevance DECIMAL(3,2),  -- 0.00 to 1.00
    format_compliance DECIMAL(3,2),
    emotional_match DECIMAL(3,2),
    missing_price BOOLEAN DEFAULT FALSE,
    incorrect_format BOOLEAN DEFAULT FALSE,
    inappropriate_tone BOOLEAN DEFAULT FALSE,
    user_rating INTEGER CHECK (user_rating BETWEEN 1 AND 5),
    completed_order BOOLEAN,
    processing_time_ms INTEGER
);

-- Таблица для статистики запросов
CREATE TABLE IF NOT EXISTS request_stats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    request_type VARCHAR(50) NOT NULL,
    success BOOLEAN DEFAULT TRUE,
    tokens_used INTEGER NOT NULL,
    user_id UUID NOT NULL,
    conversation_id UUID,
    query_text TEXT,
    matched_intent VARCHAR(100),
    completion_status VARCHAR(50),
    error_type VARCHAR(100)
);

-- Таблица для агрегированной статистики
CREATE TABLE IF NOT EXISTS daily_stats (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost_usd DECIMAL(10,4) DEFAULT 0,
    avg_response_quality DECIMAL(3,2),
    successful_orders INTEGER DEFAULT 0,
    failed_orders INTEGER DEFAULT 0,
    popular_items JSONB,
    common_issues JSONB,
    peak_hours JSONB
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_token_usage_timestamp ON token_usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_response_quality_timestamp ON response_quality(timestamp);
CREATE INDEX IF NOT EXISTS idx_request_stats_timestamp ON request_stats(timestamp);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);

-- Триггер для автоматического обновления daily_stats
CREATE OR REPLACE FUNCTION update_daily_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Обновляем или вставляем запись в daily_stats
    INSERT INTO daily_stats (date, total_requests, total_tokens, total_cost_usd)
    VALUES (
        DATE(NEW.timestamp),
        1,
        NEW.total_tokens,
        NEW.cost_usd
    )
    ON CONFLICT (date) DO UPDATE SET
        total_requests = daily_stats.total_requests + 1,
        total_tokens = daily_stats.total_tokens + NEW.total_tokens,
        total_cost_usd = daily_stats.total_cost_usd + NEW.cost_usd;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER token_usage_trigger
AFTER INSERT ON token_usage
FOR EACH ROW
EXECUTE FUNCTION update_daily_stats();
