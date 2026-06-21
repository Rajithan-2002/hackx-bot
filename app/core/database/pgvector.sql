-- pgvector.sql
-- Enable pgvector and define similarity search functions

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Vector similarity search function
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_threshold FLOAT,
  match_count INT
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
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- Index for fast vector search
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx ON document_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
