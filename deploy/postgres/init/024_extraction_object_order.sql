ALTER TABLE evidence_objects
    ADD COLUMN IF NOT EXISTS extraction_ordinal integer;

ALTER TABLE evidence_objects
    DROP CONSTRAINT IF EXISTS evidence_extraction_ordinal_valid;
ALTER TABLE evidence_objects
    ADD CONSTRAINT evidence_extraction_ordinal_valid CHECK (
        extraction_ordinal IS NULL OR extraction_ordinal >= 0
    );

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'extraction_manifests','postgres_table','Evidence Extraction',
    'Immutable ordered provenance binding from screened representation to provisional evidence',
    true,'immutable_ledger',true,
    'Object ordinal preserves byte-stable extraction reconstruction after restart'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
