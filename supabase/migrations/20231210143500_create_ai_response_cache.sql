-- Create the ai_response_cache table
CREATE TABLE IF NOT EXISTS ai_response_cache (
    id BIGSERIAL PRIMARY KEY,
    query_hash TEXT NOT NULL,
    query_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 0,
    UNIQUE(query_hash)
);

-- Create an index on query_hash for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_response_cache_query_hash ON ai_response_cache(query_hash);

-- Create an index on created_at for faster cleanup
CREATE INDEX IF NOT EXISTS idx_ai_response_cache_created_at ON ai_response_cache(created_at);

-- Add RLS policies
ALTER TABLE ai_response_cache ENABLE ROW LEVEL SECURITY;

-- Allow the service role to do everything
CREATE POLICY "Service role can do everything on ai_response_cache"
    ON ai_response_cache
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
