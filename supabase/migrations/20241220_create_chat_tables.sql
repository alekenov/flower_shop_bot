-- Создаем таблицу для кэширования ответов
CREATE TABLE IF NOT EXISTS cache_answers (
    question_hash TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    hits INTEGER DEFAULT 1,
    positive_feedback INTEGER DEFAULT 0,
    negative_feedback INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cache_last_updated ON cache_answers(last_updated);

-- Создаем таблицу для статистики чатов
CREATE TABLE IF NOT EXISTS chat_statistics (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    answered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_time_ms INTEGER,
    was_cached BOOLEAN DEFAULT FALSE,
    was_helpful BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_stats_user ON chat_statistics(user_id);
CREATE INDEX IF NOT EXISTS idx_stats_answered_at ON chat_statistics(answered_at);

-- Создаем таблицу для контекста чатов
CREATE TABLE IF NOT EXISTS chat_context (
    user_id BIGINT PRIMARY KEY,
    context JSONB NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Добавляем автоматическую очистку старых контекстов
CREATE EXTENSION IF NOT EXISTS pg_cron;
SELECT cron.schedule('cleanup-chat-context', '*/30 * * * *', 
    $$DELETE FROM chat_context WHERE last_updated < NOW() - INTERVAL '1 hour'$$
);
