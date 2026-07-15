CREATE TABLE IF NOT EXISTS evidence_review_events (
    review_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    evidence_id uuid NOT NULL REFERENCES evidence_objects(evidence_id),
    from_status text NOT NULL CHECK (from_status IN ('pending','accepted','rejected')),
    decision text NOT NULL CHECK (decision IN ('accepted','rejected')),
    reviewer_id text NOT NULL,
    rationale text NOT NULL CHECK (length(trim(rationale)) > 0),
    occurred_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS evidence_review_events_evidence_idx
    ON evidence_review_events(evidence_id, occurred_at);

DROP TRIGGER IF EXISTS evidence_review_events_immutable ON evidence_review_events;
CREATE TRIGGER evidence_review_events_immutable
    BEFORE UPDATE OR DELETE ON evidence_review_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
