ALTER TABLE scientific_representations
    ADD COLUMN IF NOT EXISTS final_url text,
    ADD COLUMN IF NOT EXISTS http_status integer
        CHECK (http_status IS NULL OR http_status BETWEEN 100 AND 599),
    ADD COLUMN IF NOT EXISTS redirect_chain jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS response_headers jsonb NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS content_encoding text,
    ADD COLUMN IF NOT EXISTS license text,
    ADD COLUMN IF NOT EXISTS source_definition_id text,
    ADD COLUMN IF NOT EXISTS query_family_id text,
    ADD COLUMN IF NOT EXISTS capture_manifest_hash text;

ALTER TABLE scientific_representations
    DROP CONSTRAINT IF EXISTS scientific_representations_capture_manifest_hash_check;

ALTER TABLE scientific_representations
    ADD CONSTRAINT scientific_representations_capture_manifest_hash_check
    CHECK (
        capture_manifest_hash IS NULL
        OR capture_manifest_hash ~ '^[0-9a-f]{64}$'
    );

COMMENT ON COLUMN scientific_representations.capture_manifest_hash IS
    'SHA-256 of the canonical raw-capture metadata manifest; NULL only for historical rows.';
