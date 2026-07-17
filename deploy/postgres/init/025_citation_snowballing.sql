CREATE TABLE IF NOT EXISTS citation_traversal_runs (
    traversal_id text PRIMARY KEY,
    discovery_run_id text NOT NULL,
    discovery_contract_id text NOT NULL,
    seed_record_id text NOT NULL,
    directions text[] NOT NULL CHECK (cardinality(directions) > 0),
    maximum_depth integer NOT NULL CHECK (maximum_depth > 0),
    retrieval_budget integer NOT NULL CHECK (retrieval_budget > 0),
    created_at timestamptz NOT NULL,
    stopping_reasons text[] NOT NULL CHECK (cardinality(stopping_reasons) > 0),
    manifest_hash text NOT NULL CHECK (length(manifest_hash) = 64),
    schema_version text NOT NULL,
    UNIQUE(discovery_run_id, seed_record_id, manifest_hash)
);

CREATE TABLE IF NOT EXISTS citation_traversal_edges (
    traversal_id text NOT NULL REFERENCES citation_traversal_runs(traversal_id),
    source_identifier text NOT NULL,
    target_identifier text NOT NULL,
    direction text NOT NULL CHECK (direction IN ('backward','forward')),
    depth integer NOT NULL CHECK (depth > 0),
    provider text NOT NULL,
    response_hash text NOT NULL CHECK (length(response_hash) = 64),
    request_url text NOT NULL CHECK (request_url LIKE 'https://%'),
    PRIMARY KEY(
        traversal_id,source_identifier,target_identifier,direction,provider
    )
);

CREATE TABLE IF NOT EXISTS citation_traversal_failures (
    traversal_id text NOT NULL REFERENCES citation_traversal_runs(traversal_id),
    provider text NOT NULL,
    identifier text NOT NULL,
    direction text NOT NULL CHECK (direction IN ('backward','forward')),
    depth integer NOT NULL CHECK (depth > 0),
    error_type text NOT NULL,
    message text NOT NULL,
    retryable boolean NOT NULL,
    PRIMARY KEY(
        traversal_id,provider,identifier,direction,depth,error_type
    )
);

DROP TRIGGER IF EXISTS citation_traversal_runs_immutable
    ON citation_traversal_runs;
CREATE TRIGGER citation_traversal_runs_immutable
    BEFORE UPDATE OR DELETE ON citation_traversal_runs
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

DROP TRIGGER IF EXISTS citation_traversal_edges_immutable
    ON citation_traversal_edges;
CREATE TRIGGER citation_traversal_edges_immutable
    BEFORE UPDATE OR DELETE ON citation_traversal_edges
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

DROP TRIGGER IF EXISTS citation_traversal_failures_immutable
    ON citation_traversal_failures;
CREATE TRIGGER citation_traversal_failures_immutable
    BEFORE UPDATE OR DELETE ON citation_traversal_failures
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES
(
    'citation_traversal_runs','postgres_table','Citation Snowballing',
    'Contract, seed, directions, limits, stopping reasons, and manifest hash',
    true,'immutable_ledger',true,
    'Reproducible traversal manifest; citations are candidates, not evidence'
),
(
    'citation_traversal_edges','postgres_table','Citation Snowballing',
    'Direction, depth, provider, response hash, and request URL',
    true,'immutable_ledger',true,
    'Provider-attributed citation candidates'
),
(
    'citation_traversal_failures','postgres_table','Citation Snowballing',
    'Provider, identifier, direction, depth, error, and retryability',
    true,'immutable_ledger',true,
    'Partial coverage and unsupported directions remain explicit'
)
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
