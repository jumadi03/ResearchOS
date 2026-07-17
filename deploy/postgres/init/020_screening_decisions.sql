CREATE TABLE IF NOT EXISTS screening_decisions (
    screening_decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_key text NOT NULL UNIQUE,
    canonical_document_id uuid NOT NULL REFERENCES scientific_documents(document_id),
    source_document_id text NOT NULL,
    inspection_id uuid NOT NULL REFERENCES source_inspections(inspection_id),
    discovery_contract_id text NOT NULL,
    document_content_hash text NOT NULL CHECK (document_content_hash ~ '^[0-9a-f]{64}$'),
    inspection_manifest_hash text NOT NULL CHECK (inspection_manifest_hash ~ '^[0-9a-f]{64}$'),
    status text NOT NULL CHECK (status IN ('eligible','ineligible','human_review_required')),
    reasons jsonb NOT NULL,
    screener_name text NOT NULL,
    screener_version text NOT NULL,
    decided_at timestamptz NOT NULL,
    decision_hash text NOT NULL UNIQUE CHECK (decision_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(inspection_id,discovery_contract_id,screener_name,screener_version)
);

DROP TRIGGER IF EXISTS screening_decisions_immutable ON screening_decisions;
CREATE TRIGGER screening_decisions_immutable
    BEFORE UPDATE OR DELETE ON screening_decisions
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'screening_decisions','postgres_table','Scientific Screening',
    'Immutable technical, scope, evidence, and quality eligibility decisions',
    true,'immutable_ledger',true,
    'Pre-extraction decision bound to canonical document, contract, content, and inspection'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
