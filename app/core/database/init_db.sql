-- 1. Chat logs table (for Analytics)
CREATE TABLE IF NOT EXISTS chat_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  route_used TEXT NOT NULL, -- GREETING, CACHE, LLM, ERROR
  confidence FLOAT DEFAULT 0.0,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Chat cache table (for response caching)
CREATE TABLE IF NOT EXISTS chat_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_hash TEXT NOT NULL UNIQUE,
  answer TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'cache',
  usage_count INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_used TIMESTAMPTZ DEFAULT NOW()
);
