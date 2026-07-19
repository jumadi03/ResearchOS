CREATE OR REPLACE VIEW evidence_current_review_projection AS
SELECT
    e.evidence_id,
    e.human_review_status AS stored_status,
    COALESCE(r.decision, 'pending') AS projected_status,
    r.review_id,
    r.provenance_id,
    r.occurred_at,
    (e.human_review_status = COALESCE(r.decision, 'pending')) AS status_consistent
FROM evidence_objects e
JOIN extraction_manifests x
  ON x.extraction_manifest_id = e.extraction_manifest_id
LEFT JOIN LATERAL (
    SELECT
        v.review_id,
        v.decision,
        v.provenance_id,
        v.occurred_at
    FROM evidence_review_events v
    WHERE v.evidence_id = e.evidence_id
      AND v.assessment IS NOT NULL
      AND v.assessment_hash IS NOT NULL
      AND v.reviewed_statement_hash = e.content_hash
      AND v.extraction_manifest_hash = x.manifest_hash
      AND (
          v.decision = 'rejected'
          OR (
              v.decision = 'accepted'
              AND COALESCE((v.assessment->>'citation_fidelity')::boolean, false)
              AND COALESCE((v.assessment->>'context_preserved')::boolean, false)
              AND COALESCE((v.assessment->>'relevant')::boolean, false)
              AND COALESCE(v.assessment->>'epistemic_classification', 'unclear')
                    <> 'unclear'
          )
      )
    ORDER BY v.occurred_at DESC, v.created_at DESC, v.review_id DESC
    LIMIT 1
) r ON true;

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'evidence_current_review_projection','derived_index','Human Evidence Review',
    'Current evidence review state derived from the latest hash-bound admissible structured decision',
    false,'derived',true,
    'SGF-040 current-state projection; evidence_review_events remains the immutable authority'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
