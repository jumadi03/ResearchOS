CREATE TABLE IF NOT EXISTS ai_analysis_runs (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    object_id uuid NOT NULL REFERENCES canonical_objects(object_id),
    project_id text NOT NULL REFERENCES research_projects(project_id),
    action text NOT NULL,
    actor_id text NOT NULL,
    provider text NOT NULL,
    model text NOT NULL,
    prompt_hash text NOT NULL CHECK (length(prompt_hash)=64),
    output_text text NOT NULL,
    output_hash text NOT NULL CHECK (length(output_hash)=64),
    status text NOT NULL DEFAULT 'advisory' CHECK (status='advisory'),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_analysis_runs_object_idx ON ai_analysis_runs(object_id,created_at DESC);

CREATE TABLE IF NOT EXISTS ai_analysis_review_events (
    review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id uuid NOT NULL REFERENCES ai_analysis_runs(run_id),
    decision text NOT NULL CHECK (decision IN ('accepted','rejected')),
    reviewer_id text NOT NULL,
    rationale text NOT NULL CHECK (length(trim(rationale)) >= 8),
    occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_analysis_reviews_run_idx ON ai_analysis_review_events(run_id,occurred_at DESC);

DROP TRIGGER IF EXISTS ai_analysis_runs_immutable ON ai_analysis_runs;
CREATE TRIGGER ai_analysis_runs_immutable BEFORE UPDATE OR DELETE ON ai_analysis_runs
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
DROP TRIGGER IF EXISTS ai_analysis_reviews_immutable ON ai_analysis_review_events;
CREATE TRIGGER ai_analysis_reviews_immutable BEFORE UPDATE OR DELETE ON ai_analysis_review_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(resource_name,resource_kind,owner_component,responsibility,source_of_truth,lifecycle_class,active,notes)
VALUES ('ai_analysis_runs','postgres_table','product-intelligence','Immutable contextual AI advisory outputs',true,'immutable_ledger',true,'PRODUCT-001I'),
       ('ai_analysis_review_events','postgres_table','product-intelligence','Append-only human decisions on AI advisories',true,'immutable_ledger',true,'PRODUCT-001I')
ON CONFLICT(resource_name) DO UPDATE SET active=true,updated_at=now();
