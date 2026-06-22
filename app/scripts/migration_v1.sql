-- Migration Script: Add competition_id to isolate data between competitions without data loss

-- 1. Update faq_exact table
ALTER TABLE faq_exact ADD COLUMN IF NOT EXISTS competition_id VARCHAR(50);

-- Set existing FAQs to 'hackx' by default (assuming existing exact FAQs were for HackX)
UPDATE faq_exact SET competition_id = 'hackx' WHERE competition_id IS NULL;

-- 2. Update document_chunks table (metadata JSONB column)
-- We use the 'source' key in the metadata JSONB to determine the competition.
UPDATE document_chunks
SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{competition_id}', '"hackx"')
WHERE metadata->>'source' IN ('hackx_faq.md', 'sample_faq.md', 'timeline.md')
  AND (metadata->>'competition_id') IS NULL;

UPDATE document_chunks
SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{competition_id}', '"hackxjr"')
WHERE metadata->>'source' = 'hackx_jr_faq.md'
  AND (metadata->>'competition_id') IS NULL;

-- Fallback for any other chunks (assign to hackx)
UPDATE document_chunks
SET metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{competition_id}', '"hackx"')
WHERE (metadata->>'competition_id') IS NULL;

-- 3. Update the match_documents RPC to filter by competition_id
DROP FUNCTION IF EXISTS match_documents(vector, double precision, integer);

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_threshold FLOAT,
  match_count INT,
  filter_competition_id TEXT
)
RETURNS TABLE (
  id UUID,
  chunk_text TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    chunk_text,
    metadata,
    1 - (embedding <=> query_embedding) AS similarity
  FROM document_chunks
  WHERE 1 - (embedding <=> query_embedding) > match_threshold
    AND metadata->>'competition_id' = filter_competition_id
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- 4. Truncate chat_cache to prevent cross-competition cache hits
-- (The application logic will be updated to include competition_id in the cache hash)
TRUNCATE TABLE chat_cache;
