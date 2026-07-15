ALTER TABLE embedding_index
    DROP CONSTRAINT IF EXISTS embedding_index_object_type_object_id_model_key;
ALTER TABLE embedding_index
    ADD CONSTRAINT embedding_index_canonical_content_model_key
    UNIQUE(canonical_object_id, content_hash, model);
CREATE INDEX IF NOT EXISTS embedding_index_object_lookup_idx
    ON embedding_index(canonical_object_id, model, created_at DESC);

ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS deduplication_key text;
CREATE UNIQUE INDEX IF NOT EXISTS background_jobs_deduplication_key_idx
    ON background_jobs(deduplication_key) WHERE deduplication_key IS NOT NULL;
