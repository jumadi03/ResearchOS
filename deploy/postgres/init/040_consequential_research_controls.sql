CREATE TABLE consequential_research_profiles (
    profile_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_key text NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    risk_class text NOT NULL CHECK (risk_class IN (
        'medical','legal','safety_critical','human_subject',
        'regulatory','other_consequential'
    )),
    jurisdiction text NOT NULL CHECK (length(btrim(jurisdiction)) > 0),
    required_reviewer_quorum integer NOT NULL DEFAULT 2
        CHECK (required_reviewer_quorum >= 2),
    required_qualification_kind text NOT NULL
        CHECK (length(btrim(required_qualification_kind)) > 0),
    require_unanimous_review boolean NOT NULL DEFAULT true,
    require_ethics_reference boolean NOT NULL DEFAULT true,
    require_distinct_release_authority boolean NOT NULL DEFAULT true,
    decision_validity_days integer NOT NULL CHECK (decision_validity_days > 0),
    policy_document_id text NOT NULL CHECK (length(btrim(policy_document_id)) > 0),
    policy_document_hash text NOT NULL
        CHECK (policy_document_hash ~ '^[0-9a-f]{64}$'),
    effective_from timestamptz NOT NULL,
    retired_at timestamptz,
    created_by text NOT NULL CHECK (length(btrim(created_by)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(profile_key, version),
    CHECK (retired_at IS NULL OR retired_at > effective_from)
);

CREATE TABLE project_consequential_profiles (
    assignment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id text NOT NULL REFERENCES research_projects(project_id),
    profile_id uuid NOT NULL REFERENCES consequential_research_profiles(profile_id),
    activated_by text NOT NULL CHECK (length(btrim(activated_by)) > 0),
    activated_at timestamptz NOT NULL,
    deactivated_at timestamptz,
    rationale text NOT NULL CHECK (length(btrim(rationale)) > 0),
    UNIQUE(project_id, profile_id, activated_at),
    CHECK (deactivated_at IS NULL OR deactivated_at > activated_at)
);

CREATE UNIQUE INDEX project_active_consequential_profile_idx
    ON project_consequential_profiles(project_id)
    WHERE deactivated_at IS NULL;

CREATE TABLE human_authorities (
    authority_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_user_id uuid UNIQUE REFERENCES workspace_users(user_id),
    stable_subject_id text NOT NULL UNIQUE,
    display_name text NOT NULL CHECK (length(btrim(display_name)) > 0),
    authority_status text NOT NULL DEFAULT 'active'
        CHECK (authority_status IN ('active','suspended','retired')),
    identity_verified_at timestamptz NOT NULL,
    identity_verified_by text NOT NULL
        CHECK (length(btrim(identity_verified_by)) > 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE authority_qualifications (
    qualification_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    authority_id uuid NOT NULL REFERENCES human_authorities(authority_id),
    qualification_kind text NOT NULL,
    issuing_body text NOT NULL CHECK (length(btrim(issuing_body)) > 0),
    jurisdiction text NOT NULL CHECK (length(btrim(jurisdiction)) > 0),
    scope jsonb NOT NULL CHECK (jsonb_typeof(scope) = 'object'),
    credential_reference text NOT NULL,
    credential_hash text NOT NULL CHECK (credential_hash ~ '^[0-9a-f]{64}$'),
    valid_from timestamptz NOT NULL,
    valid_until timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','suspended','revoked','expired')),
    verified_by text NOT NULL CHECK (length(btrim(verified_by)) > 0),
    verified_at timestamptz NOT NULL,
    UNIQUE(authority_id, qualification_kind, credential_hash),
    CHECK (valid_until > valid_from)
);

CREATE INDEX authority_qualifications_current_idx
    ON authority_qualifications(authority_id, qualification_kind, valid_until)
    WHERE status = 'active';

CREATE TABLE ethics_approvals (
    ethics_approval_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id text NOT NULL REFERENCES research_projects(project_id),
    protocol_identifier text NOT NULL,
    issuing_body text NOT NULL CHECK (length(btrim(issuing_body)) > 0),
    jurisdiction text NOT NULL CHECK (length(btrim(jurisdiction)) > 0),
    decision text NOT NULL CHECK (decision IN ('approved','waived')),
    scope jsonb NOT NULL CHECK (jsonb_typeof(scope) = 'object'),
    document_reference text NOT NULL,
    document_hash text NOT NULL CHECK (document_hash ~ '^[0-9a-f]{64}$'),
    valid_from timestamptz NOT NULL,
    valid_until timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','suspended','revoked','expired','superseded')),
    recorded_by text NOT NULL CHECK (length(btrim(recorded_by)) > 0),
    recorded_at timestamptz NOT NULL,
    supersedes_ethics_approval_id uuid REFERENCES ethics_approvals(ethics_approval_id),
    UNIQUE(project_id, protocol_identifier, document_hash),
    CHECK (valid_until > valid_from),
    CHECK (supersedes_ethics_approval_id IS NULL
        OR supersedes_ethics_approval_id <> ethics_approval_id)
);

CREATE INDEX ethics_approvals_current_idx
    ON ethics_approvals(project_id, valid_until)
    WHERE status = 'active';

CREATE TABLE scientific_decisions (
    decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id text NOT NULL REFERENCES research_projects(project_id),
    profile_id uuid NOT NULL REFERENCES consequential_research_profiles(profile_id),
    decision_type text NOT NULL CHECK (decision_type IN (
        'evidence','theory','validation','artifact_transition',
        'publication_release','governance'
    )),
    target_type text NOT NULL CHECK (length(btrim(target_type)) > 0),
    target_id text NOT NULL CHECK (length(btrim(target_id)) > 0),
    target_version text NOT NULL CHECK (length(btrim(target_version)) > 0),
    target_content_hash text NOT NULL
        CHECK (target_content_hash ~ '^[0-9a-f]{64}$'),
    proposed_decision text NOT NULL CHECK (length(btrim(proposed_decision)) > 0),
    proposer_authority_id uuid NOT NULL REFERENCES human_authorities(authority_id),
    release_authority_id uuid REFERENCES human_authorities(authority_id),
    rationale text NOT NULL CHECK (length(btrim(rationale)) > 0),
    policy_snapshot_hash text NOT NULL
        CHECK (policy_snapshot_hash ~ '^[0-9a-f]{64}$'),
    opened_at timestamptz NOT NULL,
    review_due_at timestamptz NOT NULL,
    valid_until timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(project_id, decision_type, target_type, target_id, target_content_hash),
    CHECK (review_due_at > opened_at),
    CHECK (valid_until >= review_due_at),
    CHECK (release_authority_id IS NULL
        OR release_authority_id <> proposer_authority_id)
);

CREATE TABLE decision_ethics_references (
    decision_id uuid NOT NULL REFERENCES scientific_decisions(decision_id),
    ethics_approval_id uuid NOT NULL REFERENCES ethics_approvals(ethics_approval_id),
    linked_by text NOT NULL CHECK (length(btrim(linked_by)) > 0),
    linked_at timestamptz NOT NULL,
    PRIMARY KEY(decision_id, ethics_approval_id)
);

CREATE TABLE conflict_of_interest_declarations (
    declaration_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id uuid NOT NULL REFERENCES scientific_decisions(decision_id),
    authority_id uuid NOT NULL REFERENCES human_authorities(authority_id),
    declaration text NOT NULL CHECK (declaration IN (
        'no_conflict','managed_conflict','unresolved_conflict'
    )),
    details text NOT NULL,
    mitigation text,
    declared_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id),
    UNIQUE(decision_id, authority_id),
    CHECK (
        declaration <> 'managed_conflict'
        OR length(btrim(COALESCE(mitigation, ''))) > 0
    )
);

CREATE TABLE decision_review_votes (
    vote_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id uuid NOT NULL REFERENCES scientific_decisions(decision_id),
    reviewer_authority_id uuid NOT NULL REFERENCES human_authorities(authority_id),
    vote text NOT NULL CHECK (vote IN ('approve','reject','abstain')),
    rationale text NOT NULL CHECK (length(btrim(rationale)) > 0),
    reviewed_target_hash text NOT NULL
        CHECK (reviewed_target_hash ~ '^[0-9a-f]{64}$'),
    occurred_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id),
    UNIQUE(decision_id, reviewer_authority_id)
);

CREATE TABLE decision_quorum_results (
    quorum_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id uuid NOT NULL REFERENCES scientific_decisions(decision_id),
    evaluated_at timestamptz NOT NULL,
    passed boolean NOT NULL,
    approval_count integer NOT NULL CHECK (approval_count >= 0),
    rejection_count integer NOT NULL CHECK (rejection_count >= 0),
    distinct_reviewer_count integer NOT NULL CHECK (distinct_reviewer_count >= 0),
    ethics_satisfied boolean NOT NULL,
    qualifications_satisfied boolean NOT NULL,
    conflicts_satisfied boolean NOT NULL,
    release_authority_satisfied boolean NOT NULL,
    freshness_satisfied boolean NOT NULL,
    failure_reasons jsonb NOT NULL CHECK (jsonb_typeof(failure_reasons) = 'array'),
    evaluated_by text NOT NULL CHECK (length(btrim(evaluated_by)) > 0),
    result_hash text NOT NULL UNIQUE CHECK (result_hash ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(decision_id, evaluated_at)
);

CREATE TABLE decision_appeals (
    appeal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    contested_decision_id uuid NOT NULL REFERENCES scientific_decisions(decision_id),
    appellant_authority_id uuid NOT NULL REFERENCES human_authorities(authority_id),
    grounds text NOT NULL CHECK (length(btrim(grounds)) > 0),
    requested_remedy text NOT NULL CHECK (length(btrim(requested_remedy)) > 0),
    supporting_evidence jsonb NOT NULL CHECK (jsonb_typeof(supporting_evidence) = 'array'),
    filed_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id)
);

CREATE TABLE decision_appeal_events (
    appeal_event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    appeal_id uuid NOT NULL REFERENCES decision_appeals(appeal_id),
    event_type text NOT NULL CHECK (event_type IN (
        'filed','accepted_for_review','rejected','resolved_upheld',
        'resolved_overturned','resolved_remanded'
    )),
    actor_authority_id uuid NOT NULL REFERENCES human_authorities(authority_id),
    rationale text NOT NULL CHECK (length(btrim(rationale)) > 0),
    resulting_decision_id uuid REFERENCES scientific_decisions(decision_id),
    occurred_at timestamptz NOT NULL,
    provenance_id uuid NOT NULL UNIQUE REFERENCES provenance_events(provenance_id)
);

CREATE INDEX scientific_decisions_target_idx
    ON scientific_decisions(project_id, target_type, target_id, opened_at DESC);
CREATE INDEX decision_review_votes_decision_idx
    ON decision_review_votes(decision_id, occurred_at);
CREATE INDEX decision_quorum_results_decision_idx
    ON decision_quorum_results(decision_id, evaluated_at DESC);
CREATE INDEX decision_appeal_events_appeal_idx
    ON decision_appeal_events(appeal_id, occurred_at);

CREATE TRIGGER consequential_research_profiles_immutable
    BEFORE UPDATE OR DELETE ON consequential_research_profiles
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER project_consequential_profiles_immutable
    BEFORE UPDATE OR DELETE ON project_consequential_profiles
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER human_authorities_immutable
    BEFORE UPDATE OR DELETE ON human_authorities
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER authority_qualifications_immutable
    BEFORE UPDATE OR DELETE ON authority_qualifications
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER ethics_approvals_immutable
    BEFORE UPDATE OR DELETE ON ethics_approvals
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER scientific_decisions_immutable
    BEFORE UPDATE OR DELETE ON scientific_decisions
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER decision_ethics_references_immutable
    BEFORE UPDATE OR DELETE ON decision_ethics_references
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER conflict_of_interest_declarations_immutable
    BEFORE UPDATE OR DELETE ON conflict_of_interest_declarations
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER decision_review_votes_immutable
    BEFORE UPDATE OR DELETE ON decision_review_votes
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER decision_quorum_results_immutable
    BEFORE UPDATE OR DELETE ON decision_quorum_results
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER decision_appeals_immutable
    BEFORE UPDATE OR DELETE ON decision_appeals
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();
CREATE TRIGGER decision_appeal_events_immutable
    BEFORE UPDATE OR DELETE ON decision_appeal_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

CREATE VIEW consequential_decision_readiness AS
SELECT
    d.decision_id,
    d.project_id,
    d.decision_type,
    d.target_type,
    d.target_id,
    d.target_content_hash,
    p.required_reviewer_quorum,
    vote.approval_count,
    vote.rejection_count,
    vote.distinct_reviewer_count,
    COALESCE(vote.reviewers_qualified, false) AS qualifications_satisfied,
    COALESCE(vote.conflicts_clear, false) AS conflicts_satisfied,
    (
        NOT p.require_ethics_reference
        OR EXISTS (
            SELECT 1
            FROM decision_ethics_references der
            JOIN ethics_approvals ea
              ON ea.ethics_approval_id = der.ethics_approval_id
            WHERE der.decision_id = d.decision_id
              AND ea.project_id = d.project_id
              AND ea.status = 'active'
              AND ea.valid_from <= now()
              AND ea.valid_until > now()
        )
    ) AS ethics_satisfied,
    (
        NOT p.require_distinct_release_authority
        OR (
            d.decision_type <> 'publication_release'
            OR (
                d.release_authority_id IS NOT NULL
                AND d.release_authority_id <> d.proposer_authority_id
                AND NOT EXISTS (
                    SELECT 1 FROM decision_review_votes drv
                    WHERE drv.decision_id = d.decision_id
                      AND drv.reviewer_authority_id = d.release_authority_id
                )
            )
        )
    ) AS release_authority_satisfied,
    (d.valid_until > now() AND d.review_due_at > now()) AS freshness_satisfied,
    (
        vote.approval_count >= p.required_reviewer_quorum
        AND vote.distinct_reviewer_count >= p.required_reviewer_quorum
        AND (
            NOT p.require_unanimous_review
            OR vote.rejection_count = 0
        )
        AND COALESCE(vote.reviewers_qualified, false)
        AND COALESCE(vote.conflicts_clear, false)
        AND (
            NOT p.require_ethics_reference
            OR EXISTS (
                SELECT 1
                FROM decision_ethics_references der
                JOIN ethics_approvals ea
                  ON ea.ethics_approval_id = der.ethics_approval_id
                WHERE der.decision_id = d.decision_id
                  AND ea.project_id = d.project_id
                  AND ea.status = 'active'
                  AND ea.valid_from <= now()
                  AND ea.valid_until > now()
            )
        )
        AND (
            NOT p.require_distinct_release_authority
            OR d.decision_type <> 'publication_release'
            OR (
                d.release_authority_id IS NOT NULL
                AND d.release_authority_id <> d.proposer_authority_id
                AND NOT EXISTS (
                    SELECT 1 FROM decision_review_votes drv
                    WHERE drv.decision_id = d.decision_id
                      AND drv.reviewer_authority_id = d.release_authority_id
                )
            )
        )
        AND d.valid_until > now()
        AND d.review_due_at > now()
    ) AS ready
FROM scientific_decisions d
JOIN consequential_research_profiles p ON p.profile_id = d.profile_id
LEFT JOIN LATERAL (
    SELECT
        count(*) FILTER (WHERE drv.vote = 'approve')::integer AS approval_count,
        count(*) FILTER (WHERE drv.vote = 'reject')::integer AS rejection_count,
        count(DISTINCT drv.reviewer_authority_id)::integer AS distinct_reviewer_count,
        bool_and(
            drv.reviewer_authority_id <> d.proposer_authority_id
            AND drv.reviewed_target_hash = d.target_content_hash
            AND ha.authority_status = 'active'
            AND EXISTS (
                SELECT 1 FROM authority_qualifications aq
                WHERE aq.authority_id = drv.reviewer_authority_id
                  AND aq.qualification_kind = p.required_qualification_kind
                  AND aq.jurisdiction = p.jurisdiction
                  AND aq.status = 'active'
                  AND aq.valid_from <= drv.occurred_at
                  AND aq.valid_until > drv.occurred_at
            )
        ) FILTER (WHERE drv.vote = 'approve') AS reviewers_qualified,
        bool_and(
            EXISTS (
                SELECT 1 FROM conflict_of_interest_declarations coi
                WHERE coi.decision_id = d.decision_id
                  AND coi.authority_id = drv.reviewer_authority_id
                  AND coi.declaration IN ('no_conflict','managed_conflict')
            )
        ) FILTER (WHERE drv.vote = 'approve') AS conflicts_clear
    FROM decision_review_votes drv
    JOIN human_authorities ha
      ON ha.authority_id = drv.reviewer_authority_id
    WHERE drv.decision_id = d.decision_id
) vote ON true;

CREATE OR REPLACE FUNCTION assert_consequential_decision_ready(
    p_decision_id uuid
) RETURNS void AS $$
DECLARE
    readiness consequential_decision_readiness%ROWTYPE;
BEGIN
    SELECT * INTO readiness
    FROM consequential_decision_readiness
    WHERE decision_id = p_decision_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'consequential decision % does not exist', p_decision_id;
    END IF;
    IF NOT readiness.ready THEN
        RAISE EXCEPTION
            'consequential decision % is not ready: approvals %, rejections %, reviewers %, ethics %, qualifications %, conflicts %, release authority %, freshness %',
            p_decision_id, readiness.approval_count, readiness.rejection_count,
            readiness.distinct_reviewer_count, readiness.ethics_satisfied,
            readiness.qualifications_satisfied, readiness.conflicts_satisfied,
            readiness.release_authority_satisfied, readiness.freshness_satisfied;
    END IF;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION enforce_consequential_publication_gate()
RETURNS trigger AS $$
DECLARE
    active_profile uuid;
    release_decision uuid;
BEGIN
    IF NEW.to_status <> 'published' THEN
        RETURN NEW;
    END IF;
    SELECT pcp.profile_id INTO active_profile
    FROM research_artifacts ra
    JOIN project_consequential_profiles pcp
      ON pcp.project_id = ra.project_id
     AND pcp.deactivated_at IS NULL
    WHERE ra.artifact_id = NEW.artifact_id;
    IF active_profile IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT d.decision_id INTO release_decision
    FROM scientific_decisions d
    WHERE d.project_id = (
        SELECT project_id FROM research_artifacts
        WHERE artifact_id = NEW.artifact_id
    )
      AND d.profile_id = active_profile
      AND d.decision_type = 'publication_release'
      AND d.target_id = NEW.artifact_id::text
    ORDER BY d.opened_at DESC
    LIMIT 1;
    IF release_decision IS NULL THEN
        RAISE EXCEPTION
            'publication blocked: consequential release decision is missing';
    END IF;
    PERFORM assert_consequential_decision_ready(release_decision);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER artifact_consequential_publication_gate
    BEFORE INSERT ON artifact_lifecycle_events
    FOR EACH ROW EXECUTE FUNCTION enforce_consequential_publication_gate();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES
('consequential_research_profiles','postgres_table','Human Authority',
 'Versioned fail-closed control profiles for consequential research',
 true,'immutable_ledger',true,'SGF-020C normative profile registry'),
('human_authorities','postgres_table','Human Authority',
 'Verified stable human identities for material scientific authority',
 true,'immutable_ledger',true,'Application roles alone do not establish authority'),
('authority_qualifications','postgres_table','Human Authority',
 'Scoped and expiring authority qualifications',
 true,'immutable_ledger',true,'Qualification must match profile and jurisdiction'),
('ethics_approvals','postgres_table','Research Ethics',
 'Scoped, hash-bound, and expiring ethics approvals or waivers',
 true,'immutable_ledger',true,'Missing or expired ethics fails closed'),
('scientific_decisions','postgres_table','Human Authority',
 'Immutable material decisions bound to target, policy, profile, and provenance',
 true,'immutable_ledger',true,'Cross-object canonical decision registry'),
('decision_review_votes','postgres_table','Human Authority',
 'Independent attributed reviewer votes for material decisions',
 true,'immutable_ledger',true,'Unique human authority per decision'),
('decision_quorum_results','postgres_table','Human Authority',
 'Immutable snapshots of consequential decision quorum evaluation',
 true,'immutable_ledger',true,'Readiness is derived by database policy'),
('decision_appeals','postgres_table','Human Authority',
 'Immutable appeal cases linked to contested decisions',
 true,'immutable_ledger',true,'Appeals never overwrite original decisions'),
('consequential_decision_readiness','derived_index','Human Authority',
 'Current fail-closed decision readiness across quorum, ethics, COI, authority, and expiry',
 false,'derived',true,'Used by consequential publication gate')
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
