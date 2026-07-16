CREATE TABLE IF NOT EXISTS scientific_identifiers (
    identifier_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES scientific_documents(document_id)
        DEFERRABLE INITIALLY DEFERRED,
    identifier_type text NOT NULL,
    normalized_value text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(identifier_type,normalized_value)
);

CREATE TABLE IF NOT EXISTS identity_resolution_events (
    resolution_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id uuid NOT NULL REFERENCES canonical_objects(object_id),
    record_id text NOT NULL,
    match_kind text NOT NULL CHECK (match_kind IN ('exact','possible','unique')),
    match_basis text NOT NULL,
    rationale text NOT NULL,
    compared_identifiers jsonb NOT NULL,
    decision_hash text NOT NULL UNIQUE CHECK (decision_hash ~ '^[0-9a-f]{64}$'),
    resolved_at timestamptz NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS identity_resolution_events_immutable
    ON identity_resolution_events;
CREATE TRIGGER identity_resolution_events_immutable
    BEFORE UPDATE OR DELETE ON identity_resolution_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES
('scientific_identifiers','postgres_table','Identity Resolution',
 'Unique external identifier aliases for canonical scientific UUIDs',
 true,'canonical',true,'DOI and provider identifiers are aliases, never primary identity'),
('identity_resolution_events','postgres_table','Identity Resolution',
 'Immutable exact, possible, and unique resolution decisions',
 true,'immutable_ledger',true,'Every decision retains basis, rationale, identifiers, and hash')
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
