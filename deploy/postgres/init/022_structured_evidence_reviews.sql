ALTER TABLE evidence_review_events
    ADD COLUMN IF NOT EXISTS assessment jsonb,
    ADD COLUMN IF NOT EXISTS assessment_hash text,
    ADD COLUMN IF NOT EXISTS reviewed_statement_hash text,
    ADD COLUMN IF NOT EXISTS extraction_manifest_hash text;

ALTER TABLE evidence_review_events
    ADD CONSTRAINT evidence_review_assessment_hash_format CHECK (
        assessment_hash IS NULL OR assessment_hash ~ '^[0-9a-f]{64}$'
    ),
    ADD CONSTRAINT evidence_review_statement_hash_format CHECK (
        reviewed_statement_hash IS NULL
        OR reviewed_statement_hash ~ '^[0-9a-f]{64}$'
    ),
    ADD CONSTRAINT evidence_review_manifest_hash_format CHECK (
        extraction_manifest_hash IS NULL
        OR extraction_manifest_hash ~ '^[0-9a-f]{64}$'
    );

UPDATE evidence_objects e
SET human_review_status='pending'
WHERE human_review_status='accepted'
  AND NOT EXISTS (
      SELECT 1 FROM evidence_review_events r
      WHERE r.evidence_id=e.evidence_id AND r.decision='accepted'
        AND r.assessment_hash IS NOT NULL
  );

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'evidence_review_events','postgres_table','Human Evidence Review',
    'Immutable attributed structured review of citation fidelity, context, relevance, confidence, and epistemic classification',
    true,'immutable_ledger',true,
    'Review is bound to exact statement and extraction-manifest hashes'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
