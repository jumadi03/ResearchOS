CREATE TABLE scientific_impact_review_resolutions (
    resolution_id text PRIMARY KEY,
    change_id text NOT NULL UNIQUE REFERENCES scientific_changes(change_id),
    decision text NOT NULL CHECK(decision IN (
        'investigate','no_action','evidence_review_required',
        'publication_review_required'
    )),
    reviewer_id text NOT NULL CHECK(length(btrim(reviewer_id)) > 0),
    rationale text NOT NULL CHECK(length(btrim(rationale)) > 0),
    occurred_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id)
);

CREATE TRIGGER scientific_impact_review_resolutions_immutable
    BEFORE UPDATE OR DELETE ON scientific_impact_review_resolutions
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'scientific_impact_review_resolutions','postgres_table',
    'Continuous Monitoring',
    'Human triage decisions for retraction impact-review tasks',
    true,'immutable_ledger',true,
    'Retraction signals create review work; resolutions do not mutate evidence or publications'
);
