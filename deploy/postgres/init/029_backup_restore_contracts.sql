ALTER TABLE backup_runs
    ADD COLUMN IF NOT EXISTS backup_set_id text,
    ADD COLUMN IF NOT EXISTS backup_set_hash text,
    ADD COLUMN IF NOT EXISTS manifest_path text,
    ADD COLUMN IF NOT EXISTS integrity_verified boolean NOT NULL DEFAULT false;

ALTER TABLE backup_runs DROP CONSTRAINT IF EXISTS backup_runs_set_identity_check;
ALTER TABLE backup_runs ADD CONSTRAINT backup_runs_set_identity_check CHECK (
    (
        backup_set_id IS NULL
        AND backup_set_hash IS NULL
        AND manifest_path IS NULL
        AND NOT integrity_verified
    )
    OR (
        length(trim(backup_set_id)) > 0
        AND length(backup_set_hash) = 64
        AND backup_set_hash ~ '^[0-9a-f]{64}$'
        AND length(trim(manifest_path)) > 0
        AND integrity_verified
        AND status = 'completed'
        AND database_verified
        AND minio_verified
        AND knowledge_verified
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS backup_runs_set_id_unique
    ON backup_runs(backup_set_id) WHERE backup_set_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS backup_runs_set_hash_unique
    ON backup_runs(backup_set_hash) WHERE backup_set_hash IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS backup_runs_id_set_hash_unique
    ON backup_runs(backup_id, backup_set_hash);

CREATE TABLE IF NOT EXISTS backup_restore_verifications (
    verification_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_id uuid NOT NULL,
    backup_set_hash text NOT NULL
        CHECK (
            length(backup_set_hash) = 64
            AND backup_set_hash ~ '^[0-9a-f]{64}$'
        ),
    target_kind text NOT NULL CHECK (target_kind = 'isolated'),
    target_identifier text NOT NULL CHECK (length(trim(target_identifier)) > 0),
    components text[] NOT NULL CHECK (
        cardinality(components) > 0
        AND components <@ ARRAY[
            'postgresql', 'minio', 'knowledge', 'architecture',
            'configuration', 'migration'
        ]::text[]
    ),
    outcome text NOT NULL CHECK (outcome IN ('verified', 'blocked', 'failed')),
    checks jsonb NOT NULL CHECK (
        jsonb_typeof(checks) = 'array'
        AND jsonb_array_length(checks) > 0
    ),
    actor text NOT NULL CHECK (length(trim(actor)) > 0),
    started_at timestamptz NOT NULL,
    completed_at timestamptz NOT NULL CHECK (completed_at >= started_at),
    content_hash text NOT NULL UNIQUE CHECK (
        length(content_hash) = 64
        AND content_hash ~ '^[0-9a-f]{64}$'
    ),
    FOREIGN KEY (backup_id, backup_set_hash)
        REFERENCES backup_runs(backup_id, backup_set_hash)
);

DROP TRIGGER IF EXISTS backup_restore_verifications_immutable
    ON backup_restore_verifications;
CREATE TRIGGER backup_restore_verifications_immutable
BEFORE UPDATE OR DELETE ON backup_restore_verifications
FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name, resource_kind, owner_component, responsibility,
    source_of_truth, lifecycle_class, active, notes
) VALUES
(
    'backup_restore_verifications',
    'postgres_table',
    'operations-backup',
    'Append-only evidence from isolated restore verification',
    true,
    'immutable_ledger',
    true,
    'Restore execution is introduced by a separately accepted increment'
)
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();

UPDATE storage_contract_registry SET
    responsibility='Mutable backup construction status and integrity result',
    source_of_truth=true,
    lifecycle_class='operational_staging',
    notes='Backup integrity is not restore verification; portable set identity is manifest-bound',
    updated_at=now()
WHERE resource_name='backup_runs';
