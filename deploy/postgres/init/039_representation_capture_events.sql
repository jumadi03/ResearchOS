CREATE TABLE representation_capture_events (
    capture_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    representation_id uuid NOT NULL REFERENCES scientific_representations(representation_id),
    capture_manifest_hash text NOT NULL UNIQUE
        CHECK (capture_manifest_hash ~ '^[0-9a-f]{64}$'),
    source_response_hash text NOT NULL,
    source_definition_id text NOT NULL,
    query_family_id text NOT NULL,
    captured_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX representation_capture_events_representation_idx
    ON representation_capture_events(representation_id, captured_at DESC);

CREATE TRIGGER representation_capture_events_immutable
    BEFORE UPDATE OR DELETE ON representation_capture_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'representation_capture_events','postgres_table','Representation Repository',
    'Immutable raw-capture observations for content-identical representation retrievals',
    true,'immutable_ledger',true,
    'Allows fresh capture provenance without mutating an existing content-addressed representation'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
