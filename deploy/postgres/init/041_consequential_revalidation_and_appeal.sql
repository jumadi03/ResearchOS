CREATE OR REPLACE FUNCTION enforce_quorum_result_integrity()
RETURNS trigger AS $$
DECLARE
    current_state consequential_decision_readiness%ROWTYPE;
BEGIN
    SELECT * INTO current_state
    FROM consequential_decision_readiness
    WHERE decision_id = NEW.decision_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'cannot evaluate missing decision %', NEW.decision_id;
    END IF;
    IF NEW.passed IS DISTINCT FROM current_state.ready
       OR NEW.approval_count IS DISTINCT FROM current_state.approval_count
       OR NEW.rejection_count IS DISTINCT FROM current_state.rejection_count
       OR NEW.distinct_reviewer_count IS DISTINCT FROM current_state.distinct_reviewer_count
       OR NEW.ethics_satisfied IS DISTINCT FROM current_state.ethics_satisfied
       OR NEW.qualifications_satisfied IS DISTINCT FROM current_state.qualifications_satisfied
       OR NEW.conflicts_satisfied IS DISTINCT FROM current_state.conflicts_satisfied
       OR NEW.release_authority_satisfied IS DISTINCT FROM current_state.release_authority_satisfied
       OR NEW.freshness_satisfied IS DISTINCT FROM current_state.freshness_satisfied THEN
        RAISE EXCEPTION 'quorum result does not match database-derived readiness';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER decision_quorum_results_integrity
    BEFORE INSERT ON decision_quorum_results
    FOR EACH ROW EXECUTE FUNCTION enforce_quorum_result_integrity();

CREATE OR REPLACE FUNCTION enforce_independent_appeal_resolution()
RETURNS trigger AS $$
DECLARE
    appeal decision_appeals%ROWTYPE;
    contested scientific_decisions%ROWTYPE;
BEGIN
    IF NEW.event_type NOT IN (
        'accepted_for_review','resolved_upheld',
        'resolved_overturned','resolved_remanded'
    ) THEN
        RETURN NEW;
    END IF;
    SELECT * INTO appeal FROM decision_appeals WHERE appeal_id=NEW.appeal_id;
    SELECT * INTO contested
    FROM scientific_decisions WHERE decision_id=appeal.contested_decision_id;
    IF NEW.actor_authority_id = appeal.appellant_authority_id
       OR NEW.actor_authority_id = contested.proposer_authority_id
       OR EXISTS (
           SELECT 1 FROM decision_review_votes
           WHERE decision_id=contested.decision_id
             AND reviewer_authority_id=NEW.actor_authority_id
       ) THEN
        RAISE EXCEPTION
            'appeal review authority must be independent from appellant, proposer, and original reviewers';
    END IF;
    IF NEW.event_type LIKE 'resolved_%' AND NEW.resulting_decision_id IS NULL THEN
        RAISE EXCEPTION 'resolved appeal requires resulting_decision_id';
    END IF;
    IF NEW.event_type = 'accepted_for_review'
       AND NEW.resulting_decision_id IS NOT NULL THEN
        RAISE EXCEPTION 'accepted appeal review cannot predeclare a resulting decision';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER decision_appeal_events_independence
    BEFORE INSERT ON decision_appeal_events
    FOR EACH ROW EXECUTE FUNCTION enforce_independent_appeal_resolution();

CREATE VIEW consequential_revalidation_queue AS
SELECT
    d.decision_id,
    d.project_id,
    d.decision_type,
    d.target_type,
    d.target_id,
    d.review_due_at,
    d.valid_until,
    CASE
        WHEN d.valid_until <= now() THEN 'decision_expired'
        WHEN d.review_due_at <= now() THEN 'review_overdue'
        WHEN d.review_due_at <= now() + interval '30 days' THEN 'review_due_soon'
        WHEN EXISTS (
            SELECT 1
            FROM decision_ethics_references der
            JOIN ethics_approvals ea
              ON ea.ethics_approval_id=der.ethics_approval_id
            WHERE der.decision_id=d.decision_id
              AND (
                  ea.status <> 'active'
                  OR ea.valid_until <= now()
              )
        ) THEN 'ethics_invalid'
        WHEN EXISTS (
            SELECT 1
            FROM decision_ethics_references der
            JOIN ethics_approvals ea
              ON ea.ethics_approval_id=der.ethics_approval_id
            WHERE der.decision_id=d.decision_id
              AND ea.status='active'
              AND ea.valid_until <= now() + interval '30 days'
        ) THEN 'ethics_expiring_soon'
        ELSE NULL
    END AS reason,
    CASE
        WHEN d.valid_until <= now()
          OR d.review_due_at <= now()
          OR EXISTS (
              SELECT 1
              FROM decision_ethics_references der
              JOIN ethics_approvals ea
                ON ea.ethics_approval_id=der.ethics_approval_id
              WHERE der.decision_id=d.decision_id
                AND (ea.status <> 'active' OR ea.valid_until <= now())
          )
        THEN 'blocked'
        ELSE 'action_required'
    END AS enforcement_state
FROM scientific_decisions d
WHERE d.valid_until <= now()
   OR d.review_due_at <= now() + interval '30 days'
   OR EXISTS (
       SELECT 1
       FROM decision_ethics_references der
       JOIN ethics_approvals ea
         ON ea.ethics_approval_id=der.ethics_approval_id
       WHERE der.decision_id=d.decision_id
         AND (
             ea.status <> 'active'
             OR ea.valid_until <= now() + interval '30 days'
         )
   );

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'consequential_revalidation_queue','derived_index','Human Authority',
    'Fail-closed queue for expired, overdue, and soon-due consequential decisions and ethics references',
    false,'derived',true,
    'SGF-020C revalidation work queue; scientific_decisions and ethics_approvals remain authoritative'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
