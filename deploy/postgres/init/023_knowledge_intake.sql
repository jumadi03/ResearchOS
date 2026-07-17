ALTER TABLE evidence_objects
    ADD COLUMN IF NOT EXISTS page_text_hash text,
    ADD COLUMN IF NOT EXISTS extraction_rule text;

ALTER TABLE evidence_objects
    ADD CONSTRAINT evidence_page_text_hash_format CHECK (
        page_text_hash IS NULL OR page_text_hash ~ '^[0-9a-f]{64}$'
    );

CREATE TABLE IF NOT EXISTS knowledge_intake_manifests (
    intake_manifest_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    intake_key text NOT NULL UNIQUE,
    extraction_key text NOT NULL REFERENCES extraction_manifests(extraction_key),
    extraction_manifest_hash text NOT NULL
        CHECK (extraction_manifest_hash ~ '^[0-9a-f]{64}$'),
    graph_key text NOT NULL,
    graph_content_hash text NOT NULL
        CHECK (graph_content_hash ~ '^[0-9a-f]{64}$'),
    requested_evidence_ids text[] NOT NULL
        CHECK (cardinality(requested_evidence_ids) > 0),
    admitted_evidence_ids text[] NOT NULL
        CHECK (cardinality(admitted_evidence_ids) > 0),
    decisions jsonb NOT NULL,
    actor_id text NOT NULL CHECK (length(trim(actor_id)) > 0),
    occurred_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id),
    content_hash text NOT NULL UNIQUE
        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    schema_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS knowledge_intake_manifests_immutable
    ON knowledge_intake_manifests;
CREATE TRIGGER knowledge_intake_manifests_immutable
    BEFORE UPDATE OR DELETE ON knowledge_intake_manifests
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'knowledge_intake_manifests','postgres_table','Knowledge Intake',
    'Immutable accepted-evidence registration decisions bound to review and graph provenance',
    true,'immutable_ledger',true,
    'Records admitted and excluded evidence before canonical Knowledge Layer persistence'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
