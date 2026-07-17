CREATE TABLE IF NOT EXISTS citation_traversal_candidates (
    traversal_id text NOT NULL REFERENCES citation_traversal_runs(traversal_id),
    identifier text NOT NULL,
    provider text NOT NULL,
    depth integer NOT NULL CHECK (depth > 0),
    response_hash text NOT NULL CHECK (length(response_hash) = 64),
    request_url text NOT NULL CHECK (request_url LIKE 'https://%'),
    title text,
    doi text,
    PRIMARY KEY(traversal_id,provider,identifier)
);

DROP TRIGGER IF EXISTS citation_traversal_candidates_immutable
    ON citation_traversal_candidates;
CREATE TRIGGER citation_traversal_candidates_immutable
    BEFORE UPDATE OR DELETE ON citation_traversal_candidates
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'citation_traversal_candidates','postgres_table','Citation Snowballing',
    'Provider identity, title, DOI, depth, response hash, and request URL',
    true,'immutable_ledger',true,
    'Candidate inventory returns through normal discovery and screening'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
