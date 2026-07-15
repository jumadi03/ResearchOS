DELETE FROM embedding_index WHERE model = 'health-model';
ALTER TABLE embedding_index
    ALTER COLUMN embedding TYPE vector(1536)
    USING embedding::vector(1536);
CREATE INDEX IF NOT EXISTS embedding_hnsw_cosine_idx
    ON embedding_index USING hnsw (embedding vector_cosine_ops);
