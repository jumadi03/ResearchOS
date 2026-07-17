BEGIN;

DO $$
DECLARE
    test_backup_id uuid;
    set_hash text := repeat('7', 64);
    first_run record;
    second_run record;
    third_run record;
    test_verification_id uuid;
    report_hash text := repeat('8', 64);
    checks jsonb := '[
      {"component":"architecture"},
      {"component":"configuration"},
      {"component":"knowledge"},
      {"component":"migration"},
      {"component":"minio"},
      {"component":"postgresql"}
    ]'::jsonb;
    report jsonb;
    event_to_mutate bigint;
BEGIN
    INSERT INTO backup_runs(
        backup_stamp,status,database_path,minio_path,knowledge_path,
        database_verified,minio_verified,knowledge_verified,
        backup_set_id,backup_set_hash,manifest_path,integrity_verified,
        completed_at
    ) VALUES (
        '20990101T000000Z','completed','database','minio','knowledge',
        true,true,true,'backup-set:20990101T000000Z:7777777777777777',
        set_hash,'/backups/backup-set-20990101T000000Z.json',true,now()
    ) RETURNING backup_id INTO test_backup_id;

    SELECT * INTO first_run
    FROM acquire_restore_drill_lease('coordination-healthcheck', 3600);
    IF first_run.backup_id <> test_backup_id
       OR first_run.manifest_filename <> 'backup-set-20990101T000000Z.json' THEN
        RAISE EXCEPTION 'lease did not select the canonical latest backup';
    END IF;

    BEGIN
        PERFORM * FROM acquire_restore_drill_lease('competing-healthcheck', 3600);
        RAISE EXCEPTION 'concurrent restore drill lease was accepted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'another restore drill lease is already active' THEN
                RAISE;
            END IF;
    END;

    BEGIN
        PERFORM fail_restore_drill_run(
            first_run.run_id, gen_random_uuid(), 'wrong token', 'healthcheck'
        );
        RAISE EXCEPTION 'wrong lease token was accepted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'restore drill lease token does not match' THEN
                RAISE;
            END IF;
    END;
    PERFORM fail_restore_drill_run(
        first_run.run_id, first_run.lease_token, 'expected healthcheck failure',
        'healthcheck'
    );

    SELECT * INTO second_run
    FROM acquire_restore_drill_lease('coordination-healthcheck', 3600);
    report := jsonb_build_object(
        'schema_version','1.0',
        'backup_stamp','20990101T000000Z',
        'manifest_hash',set_hash,
        'outcome','verified',
        'target_kind','isolated',
        'target_identifier','researchos_restore_drill+researchos-restore-drill',
        'components',ARRAY[
            'architecture','configuration','knowledge',
            'migration','minio','postgresql'
        ],
        'checks',checks,
        'actor','healthcheck',
        'started_at','2099-01-01T00:00:00+00:00',
        'completed_at','2099-01-01T00:01:00+00:00',
        'content_hash',report_hash,
        'restore_executed',true,
        'active_target_touched',false,
        'cleanup_verified',true,
        'ledger_written',false,
        'error',NULL,
        'attestation',jsonb_build_object(
            'algorithm','ed25519',
            'key_id','restore-ed25519-healthcheck',
            'signature','healthcheck-signature'
        )
    );
    INSERT INTO backup_restore_verifications(
        backup_id,backup_set_hash,target_kind,target_identifier,components,
        outcome,checks,actor,started_at,completed_at,content_hash,
        report,attestation_algorithm,attestation_key_id,attestation_signature
    ) VALUES (
        test_backup_id,set_hash,'isolated',
        'researchos_restore_drill+researchos-restore-drill',
        ARRAY[
            'architecture','configuration','knowledge',
            'migration','minio','postgresql'
        ],
        'verified',checks,'healthcheck',
        '2099-01-01T00:00:00+00:00','2099-01-01T00:01:00+00:00',report_hash,
        report,'ed25519','restore-ed25519-healthcheck','healthcheck-signature'
    ) RETURNING backup_restore_verifications.verification_id
      INTO test_verification_id;

    BEGIN
        UPDATE restore_drill_runs
        SET status='completed',completed_at=now(),
            report_content_hash=repeat('9',64),
            verification_id=test_verification_id
        WHERE run_id=second_run.run_id;
        RAISE EXCEPTION 'direct mismatched completion was accepted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'completed run requires matching canonical verification' THEN
                RAISE;
            END IF;
    END;

    IF complete_restore_drill_run(
        second_run.run_id, second_run.lease_token, report_hash,
        test_verification_id, 'healthcheck'
    ) <> 'completed' THEN
        RAISE EXCEPTION 'matching canonical verification did not complete the run';
    END IF;

    INSERT INTO restore_drill_runs(
        backup_id,backup_set_hash,status,owner,lease_token,
        started_at,lease_expires_at
    ) VALUES (
        test_backup_id,set_hash,'running','expired-healthcheck',gen_random_uuid(),
        now() - interval '2 hours',now() - interval '1 hour'
    );
    SELECT * INTO third_run
    FROM acquire_restore_drill_lease('post-expiry-healthcheck', 3600);
    IF NOT EXISTS (
        SELECT 1 FROM restore_drill_run_events
        WHERE event_type='lease_expired' AND actor='restore-drill-coordinator'
    ) THEN
        RAISE EXCEPTION 'expired lease was not recorded explicitly';
    END IF;
    PERFORM fail_restore_drill_run(
        third_run.run_id, third_run.lease_token,
        'healthcheck cleanup', 'healthcheck'
    );

    SELECT event_id INTO event_to_mutate
    FROM restore_drill_run_events
    ORDER BY event_id LIMIT 1;
    BEGIN
        UPDATE restore_drill_run_events
        SET actor='mutated' WHERE event_id=event_to_mutate;
        RAISE EXCEPTION 'restore drill event mutation was accepted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'provenance ledger is append-only' THEN
                RAISE;
            END IF;
    END;
END;
$$;

ROLLBACK;
