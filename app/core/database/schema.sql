-- schema.sql
-- Base table definitions for HackX Assistant

-- 1. Exact FAQ table (for tier 4 matching — no embedding needed)
CREATE TABLE IF NOT EXISTS faq_exact (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  competition_id VARCHAR(50) NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  aliases JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Document chunks table (for tier 5 vector search)
CREATE TABLE IF NOT EXISTS document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_text TEXT NOT NULL,
  metadata JSONB,
  embedding vector(1536),   -- text-embedding-3-small outputs 1536 dims
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Chat logs table (for Analytics)
CREATE TABLE IF NOT EXISTS chat_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  route_used TEXT NOT NULL, -- FAQ, VECTOR, LLM, OUT_OF_SCOPE, CACHE, UNKNOWN, RETRIEVAL_ONLY
  confidence FLOAT DEFAULT 0.0,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Chat cache table (for tier 2 Response Cache)
CREATE TABLE IF NOT EXISTS chat_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  question_hash TEXT NOT NULL UNIQUE,
  answer TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'cache',
  usage_count INT DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_used TIMESTAMPTZ DEFAULT NOW()
);
