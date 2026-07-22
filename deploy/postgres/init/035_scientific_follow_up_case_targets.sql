CREATE TABLE scientific_follow_up_case_targets (
    selection_id text PRIMARY KEY,
    resolution_id text NOT NULL UNIQUE
        REFERENCES scientific_impact_review_resolutions(resolution_id),
    target_kind text NOT NULL CHECK(target_kind IN ('evidence','publication')),
    target_object_id uuid NOT NULL REFERENCES canonical_objects(object_id),
    selector_id text NOT NULL CHECK(length(btrim(selector_id)) > 0),
    rationale text NOT NULL CHECK(length(btrim(rationale)) > 0),
    occurred_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id)
);

CREATE TRIGGER scientific_follow_up_case_targets_immutable
    BEFORE UPDATE OR DELETE ON scientific_follow_up_case_targets
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'scientific_follow_up_case_targets','postgres_table',
    'Continuous Monitoring',
    'Human-selected canonical target for an impact follow-up case',
    true,'immutable_ledger',true,
    'Target linkage precedes and does not execute lifecycle decisions'
);
