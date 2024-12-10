-- Enable pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2),
    category VARCHAR(100),
    image_url TEXT,
    in_stock BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Create trigger for updating updated_at on products
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for products
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);

-- Create knowledge_base table
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Create trigger for updating updated_at on knowledge_base
CREATE TRIGGER update_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for knowledge_base
CREATE INDEX IF NOT EXISTS idx_knowledge_base_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_tags ON knowledge_base USING GIN(tags);

-- Create function for knowledge base search
CREATE OR REPLACE FUNCTION knowledge_base_search(search_query TEXT)
RETURNS TABLE (
    id INTEGER,
    title VARCHAR(255),
    content TEXT,
    category VARCHAR(100),
    tags TEXT[],
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kb.id,
        kb.title,
        kb.content,
        kb.category,
        kb.tags,
        similarity(
            CONCAT(kb.title, ' ', kb.content),
            search_query
        ) as similarity
    FROM knowledge_base kb
    WHERE 
        CONCAT(kb.title, ' ', kb.content) ILIKE '%' || search_query || '%'
    ORDER BY similarity DESC
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- Create bot_logs table
CREATE TABLE IF NOT EXISTS bot_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    user_id BIGINT,
    chat_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Create index for bot_logs
CREATE INDEX IF NOT EXISTS idx_bot_logs_category ON bot_logs(category);
CREATE INDEX IF NOT EXISTS idx_bot_logs_level ON bot_logs(level);
CREATE INDEX IF NOT EXISTS idx_bot_logs_created_at ON bot_logs(created_at);

-- Create ai_response_cache table
CREATE TABLE IF NOT EXISTS ai_response_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) NOT NULL UNIQUE,
    query_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    hit_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW())
);

-- Create trigger for updating updated_at on ai_response_cache
CREATE TRIGGER update_ai_response_cache_updated_at
    BEFORE UPDATE ON ai_response_cache
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create indexes for ai_response_cache
CREATE INDEX IF NOT EXISTS idx_ai_response_cache_query_hash ON ai_response_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_ai_response_cache_created_at ON ai_response_cache(created_at);
