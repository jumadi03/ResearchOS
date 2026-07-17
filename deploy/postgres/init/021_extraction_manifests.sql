CREATE TABLE IF NOT EXISTS extraction_manifests (
    extraction_manifest_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_key text NOT NULL UNIQUE,
    document_id uuid NOT NULL REFERENCES scientific_documents(document_id),
    representation_id uuid NOT NULL REFERENCES scientific_representations(representation_id),
    screening_decision_id uuid NOT NULL
        REFERENCES screening_decisions(screening_decision_id),
    source_document_id text NOT NULL,
    document_content_hash text NOT NULL
        CHECK (document_content_hash ~ '^[0-9a-f]{64}$'),
    inspection_manifest_hash text NOT NULL
        CHECK (inspection_manifest_hash ~ '^[0-9a-f]{64}$'),
    parser_name text NOT NULL,
    parser_version text NOT NULL,
    configuration_hash text NOT NULL
        CHECK (configuration_hash ~ '^[0-9a-f]{64}$'),
    object_count integer NOT NULL CHECK (object_count >= 0),
    created_at timestamptz NOT NULL,
    manifest_hash text NOT NULL UNIQUE
        CHECK (manifest_hash ~ '^[0-9a-f]{64}$')
);

ALTER TABLE evidence_objects
    ADD COLUMN IF NOT EXISTS extraction_manifest_id uuid
        REFERENCES extraction_manifests(extraction_manifest_id);

ALTER TABLE evidence_objects
    DROP CONSTRAINT IF EXISTS evidence_objects_evidence_type_check;
ALTER TABLE evidence_objects
    ADD CONSTRAINT evidence_objects_evidence_type_check CHECK (
        evidence_type IN (
            'claim','evidence','method','variable','population','observation',
            'measurement','dataset','result','limitation','conclusion'
        )
    );

DROP TRIGGER IF EXISTS extraction_manifests_immutable ON extraction_manifests;
CREATE TRIGGER extraction_manifests_immutable
    BEFORE UPDATE OR DELETE ON extraction_manifests
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'extraction_manifests','postgres_table','Evidence Extraction',
    'Immutable provenance binding from screened representation to provisional evidence',
    true,'immutable_ledger',true,
    'Records parser configuration, screening authority, content identity, and manifest hash'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
