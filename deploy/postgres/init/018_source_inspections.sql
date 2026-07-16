CREATE TABLE IF NOT EXISTS source_inspections (
    inspection_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_key text NOT NULL UNIQUE,
    representation_id uuid NOT NULL
        REFERENCES scientific_representations(representation_id),
    document_id text NOT NULL,
    document_content_hash text NOT NULL
        CHECK (document_content_hash ~ '^[0-9a-f]{64}$'),
    raw_capture_manifest_hash text NOT NULL
        CHECK (raw_capture_manifest_hash ~ '^[0-9a-f]{64}$'),
    inspected_at timestamptz NOT NULL,
    inspector_name text NOT NULL,
    inspector_version text NOT NULL,
    media_type text NOT NULL,
    pdf_version text NOT NULL,
    encrypted boolean NOT NULL,
    page_count integer NOT NULL CHECK (page_count >= 0),
    document_metadata jsonb NOT NULL,
    pages jsonb NOT NULL,
    diagnostics jsonb NOT NULL,
    complete boolean NOT NULL,
    manifest_hash text NOT NULL CHECK (manifest_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(representation_id,inspector_name,inspector_version,manifest_hash)
);

DROP TRIGGER IF EXISTS source_inspections_immutable ON source_inspections;
CREATE TRIGGER source_inspections_immutable
    BEFORE UPDATE OR DELETE ON source_inspections
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'source_inspections','postgres_table','Source Inspection',
    'Immutable factual document structure and metadata observations',
    true,'immutable_ledger',true,
    'Derived only from integrity-verified representations; contains no scientific judgment'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
