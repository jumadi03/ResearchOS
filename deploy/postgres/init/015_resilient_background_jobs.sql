ALTER TABLE background_jobs
    ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS locked_by text,
    ADD COLUMN IF NOT EXISTS lease_expires_at timestamptz;

ALTER TABLE background_jobs
    DROP CONSTRAINT IF EXISTS background_jobs_status_check;
ALTER TABLE background_jobs
    ADD CONSTRAINT background_jobs_status_check
    CHECK (status IN ('pending','running','complete','failed','dead_letter'));

DROP INDEX IF EXISTS background_jobs_claim_idx;
CREATE INDEX background_jobs_claim_idx
    ON background_jobs (status, available_at, created_at);
CREATE INDEX IF NOT EXISTS background_jobs_expired_lease_idx
    ON background_jobs (lease_expires_at)
    WHERE status='running';
