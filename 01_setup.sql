-- Enable pgvector
create extension if not exists vector;

-- 1. Exact FAQ table (for tier 4 matching — no embedding needed)
create table faq_exact (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  answer text not null,
  aliases jsonb default '[]',
  created_at timestamptz default now()
);

-- 2. Document chunks table (for tier 5 vector search)
create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  chunk_text text not null,
  metadata jsonb,
  embedding vector(1536),   -- text-embedding-3-small outputs 1536 dims
  created_at timestamptz default now()
);

-- 3. Chat logs table (for Analytics)
create table chat_logs (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  answer text not null,
  route_used text not null, -- FAQ, VECTOR, LLM, OUT_OF_SCOPE
  timestamp timestamptz default now()
);

-- 4. Chat cache table (for tier 2 Response Cache)
create table chat_cache (
  id uuid primary key default gen_random_uuid(),
  question_hash text not null unique,
  answer text not null,
  usage_count int default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Vector similarity search function
create or replace function match_documents(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  chunk_text text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    id,
    chunk_text,
    metadata,
    1 - (embedding <=> query_embedding) as similarity
  from document_chunks
  where 1 - (embedding <=> query_embedding) > match_threshold
  order by embedding <=> query_embedding
  limit match_count;
$$;

-- Index for fast vector search
create index on document_chunks
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
