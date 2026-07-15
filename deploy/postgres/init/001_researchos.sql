CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS background_jobs (
    job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type text NOT NULL CHECK (job_type IN ('parse_document','normalize_metadata','index_embedding')),
    payload jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','running','complete','failed')),
    attempts integer NOT NULL DEFAULT 0,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    completed_at timestamptz
);
CREATE INDEX IF NOT EXISTS background_jobs_claim_idx ON background_jobs (status, created_at);

CREATE TABLE IF NOT EXISTS document_registry (
    document_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash text UNIQUE NOT NULL,
    object_key text NOT NULL,
    media_type text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS normalized_metadata (
    record_id text PRIMARY KEY,
    metadata jsonb NOT NULL,
    source_hash text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS embedding_index (
    embedding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    object_type text NOT NULL,
    object_id text NOT NULL,
    model text NOT NULL,
    dimensions integer NOT NULL,
    embedding vector(1536) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (object_type, object_id, model)
);
CREATE INDEX IF NOT EXISTS embedding_hnsw_cosine_idx
    ON embedding_index USING hnsw (embedding vector_cosine_ops);
