CREATE TABLE storage_tier_attestations (
    attestation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_stamp text NOT NULL CHECK (backup_stamp ~ '^\d{8}T\d{6}Z$'),
    component_name text NOT NULL CHECK (component_name IN
        ('postgresql','minio','knowledge','architecture','configuration','migration')),
    storage_tier text NOT NULL CHECK (storage_tier IN
        ('hot','archived_local','restore_required')),
    canonical_locator text NOT NULL CHECK (length(canonical_locator) BETWEEN 1 AND 512),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    verified_at timestamptz NOT NULL,
    verifier text NOT NULL CHECK (length(verifier) BETWEEN 1 AND 128),
    retention_until date,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(evidence) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (backup_stamp, component_name, storage_tier, content_sha256)
);

CREATE INDEX storage_tier_attestations_latest_idx
    ON storage_tier_attestations(component_name, storage_tier, verified_at DESC);

CREATE TRIGGER storage_tier_attestations_immutable
    BEFORE UPDATE OR DELETE ON storage_tier_attestations
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

CREATE VIEW storage_tier_current AS
SELECT DISTINCT ON (component_name, storage_tier)
       attestation_id, backup_stamp, component_name, storage_tier,
       canonical_locator, content_sha256, verified_at, verifier,
       retention_until, evidence, created_at
FROM storage_tier_attestations
ORDER BY component_name, storage_tier, verified_at DESC, created_at DESC;

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'storage_tier_attestations','postgres_table','Backup Process',
    'Append-only attestations for checksum-verified hot and off-VPS backup locations',
    true,'immutable_ledger',true,
    'Archived-local is admitted only after local checksum verification; no eviction is authorized'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
