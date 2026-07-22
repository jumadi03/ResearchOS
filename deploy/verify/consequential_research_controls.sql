\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE
    profile uuid;
    proposer uuid;
    reviewer_one uuid;
    reviewer_two uuid;
    releaser uuid;
    ethics uuid;
    decision uuid;
    provenance uuid;
    readiness boolean;
    false_snapshot_rejected boolean := false;
BEGIN
    INSERT INTO consequential_research_profiles(
        profile_key,version,name,risk_class,jurisdiction,
        required_reviewer_quorum,required_qualification_kind,
        decision_validity_days,policy_document_id,policy_document_hash,
        effective_from,created_by
    ) VALUES (
        'verification-profile',1,'Verification profile','human_subject','ID',
        2,'scientific-reviewer',30,'SGF-020C',
        encode(digest('policy','sha256'),'hex'),now(),'verification'
    ) RETURNING profile_id INTO profile;

    INSERT INTO human_authorities(
        stable_subject_id,display_name,identity_verified_at,identity_verified_by
    ) VALUES
        ('verify-proposer','Verification proposer',now(),'verification')
        RETURNING authority_id INTO proposer;
    INSERT INTO human_authorities(
        stable_subject_id,display_name,identity_verified_at,identity_verified_by
    ) VALUES
        ('verify-reviewer-one','Verification reviewer one',now(),'verification')
        RETURNING authority_id INTO reviewer_one;
    INSERT INTO human_authorities(
        stable_subject_id,display_name,identity_verified_at,identity_verified_by
    ) VALUES
        ('verify-reviewer-two','Verification reviewer two',now(),'verification')
        RETURNING authority_id INTO reviewer_two;
    INSERT INTO human_authorities(
        stable_subject_id,display_name,identity_verified_at,identity_verified_by
    ) VALUES
        ('verify-releaser','Verification releaser',now(),'verification')
        RETURNING authority_id INTO releaser;

    INSERT INTO authority_qualifications(
        authority_id,qualification_kind,issuing_body,jurisdiction,scope,
        credential_reference,credential_hash,valid_from,valid_until,
        verified_by,verified_at
    ) VALUES
        (reviewer_one,'scientific-reviewer','Verification body','ID','{}',
         'credential-one',encode(digest('credential-one','sha256'),'hex'),
         now() - interval '1 day',now() + interval '1 year','verification',now()),
        (reviewer_two,'scientific-reviewer','Verification body','ID','{}',
         'credential-two',encode(digest('credential-two','sha256'),'hex'),
         now() - interval '1 day',now() + interval '1 year','verification',now());

    INSERT INTO ethics_approvals(
        project_id,protocol_identifier,issuing_body,jurisdiction,decision,scope,
        document_reference,document_hash,valid_from,valid_until,recorded_by,recorded_at
    ) VALUES (
        'researchos-default','VERIFY-ETHICS-1','Verification ethics body','ID',
        'approved','{}','verification-ethics',
        encode(digest('ethics','sha256'),'hex'),
        now() - interval '1 day',now() + interval '1 year','verification',now()
    ) RETURNING ethics_approval_id INTO ethics;

    INSERT INTO provenance_events(
        execution_id,event_type,event_payload,occurred_at,event_hash
    ) VALUES (
        'sgf020c-verification','decision_opened','{}',now(),
        encode(digest('decision-provenance','sha256'),'hex')
    ) RETURNING provenance_id INTO provenance;

    INSERT INTO scientific_decisions(
        project_id,profile_id,decision_type,target_type,target_id,target_version,
        target_content_hash,proposed_decision,proposer_authority_id,
        release_authority_id,rationale,policy_snapshot_hash,opened_at,
        review_due_at,valid_until,provenance_id
    ) VALUES (
        'researchos-default',profile,'publication_release','artifact',
        gen_random_uuid()::text,'1',
        encode(digest('target','sha256'),'hex'),'release',proposer,releaser,
        'Verification decision',encode(digest('policy','sha256'),'hex'),
        now(),now() + interval '7 days',now() + interval '30 days',provenance
    ) RETURNING decision_id INTO decision;

    SELECT ready INTO readiness
    FROM consequential_decision_readiness WHERE decision_id = decision;
    IF readiness THEN
        RAISE EXCEPTION 'decision passed before required controls were present';
    END IF;

    INSERT INTO decision_ethics_references(
        decision_id,ethics_approval_id,linked_by,linked_at
    ) VALUES (decision,ethics,'verification',now());

    INSERT INTO provenance_events(
        execution_id,event_type,event_payload,occurred_at,event_hash
    ) VALUES
        ('sgf020c-verification','coi','{}',now(),
         encode(digest('coi-one','sha256'),'hex'))
        RETURNING provenance_id INTO provenance;
    INSERT INTO conflict_of_interest_declarations(
        decision_id,authority_id,declaration,details,declared_at,provenance_id
    ) VALUES (decision,reviewer_one,'no_conflict','None',now(),provenance);

    INSERT INTO provenance_events(
        execution_id,event_type,event_payload,occurred_at,event_hash
    ) VALUES
        ('sgf020c-verification','coi','{}',now(),
         encode(digest('coi-two','sha256'),'hex'))
        RETURNING provenance_id INTO provenance;
    INSERT INTO conflict_of_interest_declarations(
        decision_id,authority_id,declaration,details,declared_at,provenance_id
    ) VALUES (decision,reviewer_two,'no_conflict','None',now(),provenance);

    INSERT INTO provenance_events(
        execution_id,event_type,event_payload,occurred_at,event_hash
    ) VALUES
        ('sgf020c-verification','vote','{}',now(),
         encode(digest('vote-one','sha256'),'hex'))
        RETURNING provenance_id INTO provenance;
    INSERT INTO decision_review_votes(
        decision_id,reviewer_authority_id,vote,rationale,
        reviewed_target_hash,occurred_at,provenance_id
    ) VALUES (
        decision,reviewer_one,'approve','Independent verification one',
        encode(digest('target','sha256'),'hex'),now(),provenance
    );

    INSERT INTO provenance_events(
        execution_id,event_type,event_payload,occurred_at,event_hash
    ) VALUES
        ('sgf020c-verification','vote','{}',now(),
         encode(digest('vote-two','sha256'),'hex'))
        RETURNING provenance_id INTO provenance;
    INSERT INTO decision_review_votes(
        decision_id,reviewer_authority_id,vote,rationale,
        reviewed_target_hash,occurred_at,provenance_id
    ) VALUES (
        decision,reviewer_two,'approve','Independent verification two',
        encode(digest('target','sha256'),'hex'),now(),provenance
    );

    SELECT ready INTO readiness
    FROM consequential_decision_readiness WHERE decision_id = decision;
    IF NOT readiness THEN
        RAISE EXCEPTION 'decision did not pass after all required controls';
    END IF;
    PERFORM assert_consequential_decision_ready(decision);

    INSERT INTO decision_quorum_results(
        decision_id,evaluated_at,passed,approval_count,rejection_count,
        distinct_reviewer_count,ethics_satisfied,qualifications_satisfied,
        conflicts_satisfied,release_authority_satisfied,freshness_satisfied,
        failure_reasons,evaluated_by,result_hash
    ) VALUES (
        decision,now(),true,2,0,2,true,true,true,true,true,'[]',
        'verification',encode(digest('valid-quorum-result','sha256'),'hex')
    );

    BEGIN
        INSERT INTO decision_quorum_results(
            decision_id,evaluated_at,passed,approval_count,rejection_count,
            distinct_reviewer_count,ethics_satisfied,qualifications_satisfied,
            conflicts_satisfied,release_authority_satisfied,freshness_satisfied,
            failure_reasons,evaluated_by,result_hash
        ) VALUES (
            decision,now() + interval '1 second',false,0,0,0,
            false,false,false,false,false,'[\"fabricated\"]',
            'verification',encode(digest('false-quorum-result','sha256'),'hex')
        );
    EXCEPTION WHEN OTHERS THEN
        false_snapshot_rejected := true;
    END;
    IF NOT false_snapshot_rejected THEN
        RAISE EXCEPTION 'fabricated quorum result was not rejected';
    END IF;
END;
$$;

ROLLBACK;

SELECT
    (SELECT max(version) FROM schema_migrations) AS schema_version,
    to_regclass('public.consequential_research_profiles') IS NOT NULL AS profiles,
    to_regclass('public.scientific_decisions') IS NOT NULL AS decisions,
    to_regclass('public.decision_appeals') IS NOT NULL AS appeals,
    to_regclass('public.consequential_decision_readiness') IS NOT NULL AS readiness,
    to_regclass('public.consequential_revalidation_queue') IS NOT NULL AS revalidation;
