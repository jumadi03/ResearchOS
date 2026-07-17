CREATE TABLE restore_drill_schedule_state (
    schedule_name text PRIMARY KEY CHECK(schedule_name = 'canonical'),
    status text NOT NULL CHECK(status IN ('active','paused')),
    cadence_seconds integer NOT NULL CHECK(
        cadence_seconds BETWEEN 86400 AND 2678400
    ),
    next_due_at timestamptz NOT NULL,
    revision integer NOT NULL CHECK(revision > 0),
    policy_hash text NOT NULL CHECK(policy_hash ~ '^[0-9a-f]{64}$'),
    pending_run_id uuid REFERENCES restore_drill_runs(run_id),
    pending_slot_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK(
        (pending_run_id IS NULL AND pending_slot_at IS NULL)
        OR
        (pending_run_id IS NOT NULL AND pending_slot_at IS NOT NULL)
    )
);

CREATE TABLE restore_drill_schedule_events (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_name text NOT NULL DEFAULT 'canonical'
        REFERENCES restore_drill_schedule_state(schedule_name),
    event_type text NOT NULL CHECK(event_type IN (
        'configured','paused','resumed','due_acquired',
        'slot_completed','slot_failed','slot_expired'
    )),
    revision integer NOT NULL CHECK(revision > 0),
    run_id uuid REFERENCES restore_drill_runs(run_id),
    actor text NOT NULL CHECK(length(trim(actor)) > 0),
    rationale text,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    CHECK(
        event_type NOT IN ('configured','paused','resumed')
        OR (rationale IS NOT NULL AND length(trim(rationale)) > 0)
    )
);

CREATE TRIGGER restore_drill_schedule_events_immutable
    BEFORE UPDATE OR DELETE ON restore_drill_schedule_events
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

CREATE OR REPLACE FUNCTION restore_drill_schedule_policy_hash(
    p_revision integer,
    p_cadence_seconds integer
) RETURNS text
LANGUAGE sql IMMUTABLE AS $$
    SELECT encode(
        digest(
            'researchos-restore-drill-schedule-v1'
            || ':' || p_revision::text
            || ':' || p_cadence_seconds::text,
            'sha256'
        ),
        'hex'
    )
$$;

INSERT INTO restore_drill_schedule_state(
    schedule_name,status,cadence_seconds,next_due_at,revision,policy_hash
) VALUES (
    'canonical','paused',604800,now() + interval '7 days',1,
    restore_drill_schedule_policy_hash(1,604800)
);

INSERT INTO restore_drill_schedule_events(
    event_type,revision,actor,rationale,details
) VALUES (
    'configured',1,'schema-migration',
    'Initial fail-closed restore-drill schedule policy',
    jsonb_build_object('cadence_seconds',604800,'status','paused')
);

CREATE OR REPLACE FUNCTION guard_restore_drill_schedule_state()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'canonical restore drill schedule cannot be deleted';
    END IF;
    IF OLD.schedule_name <> NEW.schedule_name THEN
        RAISE EXCEPTION 'canonical restore drill schedule identity is immutable';
    END IF;
    IF NEW.policy_hash <> restore_drill_schedule_policy_hash(
        NEW.revision, NEW.cadence_seconds
    ) THEN
        RAISE EXCEPTION 'restore drill schedule policy hash is invalid';
    END IF;
    IF NEW.pending_run_id IS NOT NULL AND NEW.status <> 'active' THEN
        RAISE EXCEPTION 'paused restore drill schedule cannot retain a pending run';
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER restore_drill_schedule_state_guard
    BEFORE UPDATE OR DELETE ON restore_drill_schedule_state
    FOR EACH ROW EXECUTE FUNCTION guard_restore_drill_schedule_state();

CREATE OR REPLACE FUNCTION configure_restore_drill_schedule(
    p_cadence_seconds integer,
    p_actor text,
    p_rationale text
) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE
    current_state restore_drill_schedule_state%ROWTYPE;
    next_revision integer;
BEGIN
    IF p_cadence_seconds < 86400 OR p_cadence_seconds > 2678400 THEN
        RAISE EXCEPTION 'restore drill cadence must be between 1 and 31 days';
    END IF;
    IF p_actor IS NULL OR length(trim(p_actor)) = 0 THEN
        RAISE EXCEPTION 'restore drill schedule actor is required';
    END IF;
    IF p_rationale IS NULL OR length(trim(p_rationale)) = 0 THEN
        RAISE EXCEPTION 'restore drill schedule rationale is required';
    END IF;

    SELECT * INTO current_state
    FROM restore_drill_schedule_state
    WHERE schedule_name='canonical'
    FOR UPDATE;
    IF current_state.pending_run_id IS NOT NULL THEN
        RAISE EXCEPTION 'restore drill schedule cannot change during an active slot';
    END IF;
    next_revision := current_state.revision + 1;
    UPDATE restore_drill_schedule_state SET
        cadence_seconds=p_cadence_seconds,
        next_due_at=now() + make_interval(secs => p_cadence_seconds),
        revision=next_revision,
        policy_hash=restore_drill_schedule_policy_hash(
            next_revision,p_cadence_seconds
        ),
        updated_at=now()
    WHERE schedule_name='canonical';
    INSERT INTO restore_drill_schedule_events(
        event_type,revision,actor,rationale,details
    ) VALUES (
        'configured',next_revision,trim(p_actor),trim(p_rationale),
        jsonb_build_object('cadence_seconds',p_cadence_seconds)
    );
    RETURN next_revision;
END
$$;

CREATE OR REPLACE FUNCTION set_restore_drill_schedule_status(
    p_status text,
    p_actor text,
    p_rationale text
) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE
    current_state restore_drill_schedule_state%ROWTYPE;
BEGIN
    IF p_status NOT IN ('active','paused') THEN
        RAISE EXCEPTION 'restore drill schedule status is invalid';
    END IF;
    IF p_actor IS NULL OR length(trim(p_actor)) = 0 THEN
        RAISE EXCEPTION 'restore drill schedule actor is required';
    END IF;
    IF p_rationale IS NULL OR length(trim(p_rationale)) = 0 THEN
        RAISE EXCEPTION 'restore drill schedule rationale is required';
    END IF;
    SELECT * INTO current_state
    FROM restore_drill_schedule_state
    WHERE schedule_name='canonical'
    FOR UPDATE;
    IF current_state.status = p_status THEN
        RAISE EXCEPTION 'restore drill schedule is already %', p_status;
    END IF;
    IF current_state.pending_run_id IS NOT NULL THEN
        RAISE EXCEPTION 'restore drill schedule cannot transition during an active slot';
    END IF;
    UPDATE restore_drill_schedule_state SET
        status=p_status,
        next_due_at=CASE
            WHEN p_status='active' AND next_due_at < now() THEN now()
            ELSE next_due_at
        END,
        updated_at=now()
    WHERE schedule_name='canonical';
    INSERT INTO restore_drill_schedule_events(
        event_type,revision,actor,rationale,details
    ) VALUES (
        CASE WHEN p_status='active' THEN 'resumed' ELSE 'paused' END,
        current_state.revision,trim(p_actor),trim(p_rationale),
        jsonb_build_object('status',p_status)
    );
    RETURN p_status;
END
$$;

CREATE OR REPLACE FUNCTION advance_restore_drill_schedule_after_run()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    schedule_state restore_drill_schedule_state%ROWTYPE;
    future_due timestamptz;
    schedule_event text;
BEGIN
    IF OLD.status <> 'running' OR NEW.status NOT IN ('completed','failed') THEN
        RETURN NEW;
    END IF;
    SELECT * INTO schedule_state
    FROM restore_drill_schedule_state
    WHERE schedule_name='canonical' AND pending_run_id=NEW.run_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;
    future_due := schedule_state.pending_slot_at + make_interval(
        secs => schedule_state.cadence_seconds * (
            floor(
                greatest(
                    0,
                    extract(epoch FROM (now() - schedule_state.pending_slot_at))
                ) / schedule_state.cadence_seconds
            )::integer + 1
        )
    );
    schedule_event := CASE
        WHEN NEW.status='completed' THEN 'slot_completed'
        WHEN NEW.error='Restore drill lease expired before completion'
            THEN 'slot_expired'
        ELSE 'slot_failed'
    END;
    UPDATE restore_drill_schedule_state SET
        next_due_at=future_due,
        pending_run_id=NULL,
        pending_slot_at=NULL,
        updated_at=now()
    WHERE schedule_name='canonical';
    INSERT INTO restore_drill_schedule_events(
        event_type,revision,run_id,actor,details
    ) VALUES (
        schedule_event,schedule_state.revision,NEW.run_id,
        'restore-drill-schedule',
        jsonb_build_object(
            'scheduled_at',schedule_state.pending_slot_at,
            'next_due_at',future_due,
            'run_status',NEW.status
        )
    );
    RETURN NEW;
END
$$;

CREATE TRIGGER restore_drill_schedule_run_transition
    AFTER UPDATE ON restore_drill_runs
    FOR EACH ROW EXECUTE FUNCTION advance_restore_drill_schedule_after_run();

CREATE OR REPLACE FUNCTION acquire_due_restore_drill_lease(
    p_owner text,
    p_lease_seconds integer
) RETURNS TABLE(
    schedule_status text,
    next_due_at timestamptz,
    run_id uuid,
    lease_token uuid,
    backup_id uuid,
    backup_stamp text,
    backup_set_hash text,
    manifest_filename text,
    lease_expires_at timestamptz
)
LANGUAGE plpgsql AS $$
DECLARE
    schedule_state restore_drill_schedule_state%ROWTYPE;
    leased record;
BEGIN
    SELECT * INTO schedule_state
    FROM restore_drill_schedule_state AS s
    WHERE s.schedule_name='canonical'
    FOR UPDATE;

    IF schedule_state.pending_run_id IS NOT NULL THEN
        UPDATE restore_drill_runs AS r SET
            status='failed',
            completed_at=now(),
            error='Restore drill lease expired before completion'
        WHERE r.run_id=schedule_state.pending_run_id
          AND r.status='running'
          AND r.lease_expires_at <= now();
        IF FOUND THEN
            INSERT INTO restore_drill_run_events(
                run_id,event_type,actor,details
            ) VALUES (
                schedule_state.pending_run_id,'lease_expired',
                'restore-drill-schedule',
                jsonb_build_object('lease_expires_at','expired')
            );
        END IF;
        SELECT * INTO schedule_state
        FROM restore_drill_schedule_state AS s
        WHERE s.schedule_name='canonical'
        FOR UPDATE;
    END IF;

    IF schedule_state.status <> 'active' THEN
        RETURN QUERY SELECT
            'paused'::text,schedule_state.next_due_at,
            NULL::uuid,NULL::uuid,NULL::uuid,NULL::text,NULL::text,
            NULL::text,NULL::timestamptz;
        RETURN;
    END IF;
    IF schedule_state.pending_run_id IS NOT NULL THEN
        RETURN QUERY SELECT
            'running'::text,schedule_state.next_due_at,
            schedule_state.pending_run_id,NULL::uuid,NULL::uuid,NULL::text,
            NULL::text,NULL::text,NULL::timestamptz;
        RETURN;
    END IF;
    IF schedule_state.next_due_at > now() THEN
        RETURN QUERY SELECT
            'not_due'::text,schedule_state.next_due_at,
            NULL::uuid,NULL::uuid,NULL::uuid,NULL::text,NULL::text,
            NULL::text,NULL::timestamptz;
        RETURN;
    END IF;

    SELECT * INTO leased
    FROM acquire_restore_drill_lease(p_owner,p_lease_seconds);
    UPDATE restore_drill_schedule_state SET
        pending_run_id=leased.run_id,
        pending_slot_at=schedule_state.next_due_at,
        updated_at=now()
    WHERE schedule_name='canonical';
    INSERT INTO restore_drill_schedule_events(
        event_type,revision,run_id,actor,details
    ) VALUES (
        'due_acquired',schedule_state.revision,leased.run_id,trim(p_owner),
        jsonb_build_object(
            'scheduled_at',schedule_state.next_due_at,
            'lease_expires_at',leased.lease_expires_at
        )
    );
    RETURN QUERY SELECT
        'running'::text,schedule_state.next_due_at,
        leased.run_id,leased.lease_token,leased.backup_id,
        leased.backup_stamp,leased.backup_set_hash,
        leased.manifest_filename,leased.lease_expires_at;
END
$$;

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES
(
    'restore_drill_schedule_state','postgres_table','Operations Recovery',
    'Canonical restore-drill cadence, due time, and pending slot',
    true,'operational_staging',true,
    'Host triggers request due decisions but cannot choose scheduled time'
),
(
    'restore_drill_schedule_events','postgres_table','Operations Recovery',
    'Append-only restore-drill schedule policy and slot audit',
    true,'immutable_ledger',true,
    'Configuration and lifecycle decisions retain actor and rationale'
)
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
