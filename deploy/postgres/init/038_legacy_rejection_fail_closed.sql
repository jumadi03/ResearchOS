CREATE OR REPLACE VIEW evidence_current_review_projection AS
SELECT
    e.evidence_id,
    e.human_review_status AS stored_status,
    COALESCE(
        r.decision,
        CASE WHEN e.human_review_status = 'rejected' THEN 'rejected' ELSE 'pending' END
    ) AS projected_status,
    r.review_id,
    r.provenance_id,
    r.occurred_at,
    (
        e.human_review_status = COALESCE(
            r.decision,
            CASE WHEN e.human_review_status = 'rejected' THEN 'rejected' ELSE 'pending' END
        )
    ) AS status_consistent
FROM evidence_objects e
LEFT JOIN extraction_manifests x
  ON x.extraction_manifest_id = e.extraction_manifest_id
LEFT JOIN LATERAL (
    SELECT
        v.review_id,
        v.decision,
        v.provenance_id,
        v.occurred_at
    FROM evidence_review_events v
    WHERE v.evidence_id = e.evidence_id
      AND x.extraction_manifest_id IS NOT NULL
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

UPDATE storage_contract_registry
SET notes = 'SGF-040 current-state projection; legacy acceptance fails closed to pending while an existing rejection remains rejected',
    updated_at = now()
WHERE resource_name = 'evidence_current_review_projection';
