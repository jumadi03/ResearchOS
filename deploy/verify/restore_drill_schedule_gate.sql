BEGIN;

DO $$
DECLARE
    test_backup_id uuid;
    set_hash text := repeat('9',64);
    decision record;
    repeated record;
    event_to_mutate uuid;
BEGIN
    INSERT INTO backup_runs(
        backup_stamp,status,database_path,minio_path,knowledge_path,
        database_verified,minio_verified,knowledge_verified,
        backup_set_id,backup_set_hash,manifest_path,integrity_verified,
        completed_at
    ) VALUES (
        '20990201T000000Z','completed','database','minio','knowledge',
        true,true,true,'backup-set:20990201T000000Z:9999999999999999',
        set_hash,'/backups/backup-set-20990201T000000Z.json',true,now()
    ) RETURNING backup_id INTO test_backup_id;

    IF configure_restore_drill_schedule(
        604800,'schedule-healthcheck','verify weekly cadence'
    ) <> 2 THEN
        RAISE EXCEPTION 'schedule revision did not advance';
    END IF;
    IF set_restore_drill_schedule_status(
        'active','schedule-healthcheck','begin isolated verification'
    ) <> 'active' THEN
        RAISE EXCEPTION 'schedule did not resume';
    END IF;

    SELECT * INTO decision
    FROM acquire_due_restore_drill_lease('schedule-healthcheck',7200);
    IF decision.schedule_status <> 'not_due' OR decision.run_id IS NOT NULL THEN
        RAISE EXCEPTION 'future schedule unexpectedly acquired a lease';
    END IF;

    UPDATE restore_drill_schedule_state
    SET next_due_at=now() - interval '1 minute'
    WHERE schedule_name='canonical';

    SELECT * INTO decision
    FROM acquire_due_restore_drill_lease('schedule-healthcheck',7200);
    IF decision.schedule_status <> 'running'
       OR decision.backup_id <> test_backup_id
       OR decision.manifest_filename <> 'backup-set-20990201T000000Z.json' THEN
        RAISE EXCEPTION 'due schedule did not bind the canonical latest backup';
    END IF;

    SELECT * INTO repeated
    FROM acquire_due_restore_drill_lease('repeated-host-trigger',7200);
    IF repeated.schedule_status <> 'running'
       OR repeated.run_id <> decision.run_id
       OR repeated.lease_token IS NOT NULL THEN
        RAISE EXCEPTION 'repeated trigger disclosed or created another lease';
    END IF;

    PERFORM fail_restore_drill_run(
        decision.run_id,decision.lease_token,
        'expected schedule healthcheck failure','schedule-healthcheck'
    );
    IF EXISTS (
        SELECT 1 FROM restore_drill_schedule_state
        WHERE schedule_name='canonical'
          AND (pending_run_id IS NOT NULL OR next_due_at <= now())
    ) THEN
        RAISE EXCEPTION 'failed slot did not advance the canonical schedule';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM restore_drill_schedule_events
        WHERE run_id=decision.run_id AND event_type='slot_failed'
    ) THEN
        RAISE EXCEPTION 'failed scheduled slot was not audited';
    END IF;

    PERFORM set_restore_drill_schedule_status(
        'paused','schedule-healthcheck','finish isolated verification'
    );
    SELECT event_id INTO event_to_mutate
    FROM restore_drill_schedule_events
    ORDER BY occurred_at DESC,event_id DESC LIMIT 1;
    BEGIN
        UPDATE restore_drill_schedule_events
        SET actor='mutated' WHERE event_id=event_to_mutate;
        RAISE EXCEPTION 'schedule event mutation was accepted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'provenance ledger is append-only' THEN
                RAISE;
            END IF;
    END;
END
$$;

ROLLBACK;
