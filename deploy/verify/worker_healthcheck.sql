INSERT INTO background_jobs(job_type, payload)
VALUES
  ('normalize_metadata', '{"record_id":"health-record","metadata":{"Title":"Health Check"},"source_hash":"health-hash"}');

WITH canonical AS (
    INSERT INTO canonical_objects(object_type, stable_key, lifecycle_status)
    VALUES ('health_check', 'health:canonical-object', 'draft')
    ON CONFLICT(stable_key) DO UPDATE SET updated_at=now()
    RETURNING object_id
)
INSERT INTO background_jobs(job_type, payload)
SELECT 'index_embedding', jsonb_build_object(
    'object_type', 'health_check',
    'object_id', 'health:canonical-object',
    'canonical_object_id', object_id,
    'content_hash', 'health-content-hash',
    'model', 'health-model-1536',
    'embedding', (SELECT jsonb_agg(0.001) FROM generate_series(1,1536))
)
FROM canonical;
