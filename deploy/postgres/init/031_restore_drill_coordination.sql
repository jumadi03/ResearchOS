CREATE TABLE restore_drill_runs (
    run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_id uuid NOT NULL,
    backup_set_hash text NOT NULL,
    status text NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    owner text NOT NULL CHECK (length(trim(owner)) > 0),
    lease_token uuid NOT NULL DEFAULT gen_random_uuid(),
    lease_expires_at timestamptz NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    report_content_hash text,
    verification_id uuid REFERENCES backup_restore_verifications(verification_id),
    error text,
    FOREIGN KEY (backup_id, backup_set_hash)
        REFERENCES backup_runs(backup_id, backup_set_hash),
    CHECK (
        (
            status = 'running'
            AND completed_at IS NULL
            AND report_content_hash IS NULL
            AND verification_id IS NULL
            AND error IS NULL
            AND lease_expires_at > started_at
        )
        OR (
            status = 'completed'
            AND completed_at IS NOT NULL
            AND report_content_hash ~ '^[0-9a-f]{64}$'
            AND verification_id IS NOT NULL
            AND error IS NULL
        )
        OR (
            status = 'failed'
            AND completed_at IS NOT NULL
            AND length(trim(error)) > 0
            AND (
                (report_content_hash IS NULL AND verification_id IS NULL)
                OR (
                    report_content_hash ~ '^[0-9a-f]{64}$'
                    AND verification_id IS NOT NULL
                )
            )
        )
    )
);

CREATE UNIQUE INDEX restore_drill_runs_single_active_idx
    ON restore_drill_runs ((status))
    WHERE status = 'running';
CREATE INDEX restore_drill_runs_backup_idx
    ON restore_drill_runs (backup_id, backup_set_hash, started_at DESC);

CREATE TABLE restore_drill_run_events (
    event_id bigserial PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES restore_drill_runs(run_id),
    event_type text NOT NULL CHECK (
        event_type IN ('acquired', 'completed', 'failed', 'lease_expired')
    ),
    actor text NOT NULL CHECK (length(trim(actor)) > 0),
    occurred_at timestamptz NOT NULL DEFAULT now(),
    details jsonb NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(details) = 'object')
);

CREATE TRIGGER restore_drill_run_events_immutable
BEFORE UPDATE OR DELETE ON restore_drill_run_events
FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

CREATE OR REPLACE FUNCTION validate_restore_drill_run_transition()
RETURNS trigger AS $$
DECLARE
    backup_is_eligible boolean;
    verification_matches boolean;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'restore drill runs cannot be deleted';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF OLD.status <> 'running' OR NEW.status NOT IN ('completed', 'failed') THEN
            RAISE EXCEPTION 'invalid restore drill run lifecycle transition';
        END IF;
        IF (OLD.run_id, OLD.backup_id, OLD.backup_set_hash, OLD.owner,
            OLD.lease_token, OLD.lease_expires_at, OLD.started_at)
           IS DISTINCT FROM
           (NEW.run_id, NEW.backup_id, NEW.backup_set_hash, NEW.owner,
            NEW.lease_token, NEW.lease_expires_at, NEW.started_at) THEN
            RAISE EXCEPTION 'restore drill run identity and lease are immutable';
        END IF;
        IF NEW.status = 'completed' THEN
            IF OLD.lease_expires_at <= now() THEN
                RAISE EXCEPTION 'expired restore drill lease cannot complete';
            END IF;
            SELECT v.outcome = 'verified'
                   AND v.backup_id = OLD.backup_id
                   AND v.backup_set_hash = OLD.backup_set_hash
                   AND v.content_hash = NEW.report_content_hash
            INTO verification_matches
            FROM backup_restore_verifications AS v
            WHERE v.verification_id = NEW.verification_id;
            IF verification_matches IS DISTINCT FROM true THEN
                RAISE EXCEPTION 'completed run requires matching canonical verification';
            END IF;
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.status <> 'running' THEN
        RAISE EXCEPTION 'new restore drill runs must begin as running';
    END IF;
    SELECT status = 'completed'
           AND integrity_verified
           AND database_verified
           AND minio_verified
           AND knowledge_verified
    INTO backup_is_eligible
    FROM backup_runs
    WHERE backup_id = NEW.backup_id
      AND backup_set_hash = NEW.backup_set_hash;
    IF backup_is_eligible IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'restore drill run requires an eligible canonical backup';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER restore_drill_runs_transition_guard
BEFORE INSERT OR UPDATE OR DELETE ON restore_drill_runs
FOR EACH ROW EXECUTE FUNCTION validate_restore_drill_run_transition();

CREATE OR REPLACE FUNCTION acquire_restore_drill_lease(
    p_owner text,
    p_lease_seconds integer
)
RETURNS TABLE (
    run_id uuid,
    lease_token uuid,
    backup_id uuid,
    backup_stamp text,
    backup_set_hash text,
    manifest_filename text,
    lease_expires_at timestamptz
) AS $$
DECLARE
    v_run_id uuid;
    v_lease_token uuid;
    v_backup_id uuid;
    v_backup_stamp text;
    v_backup_set_hash text;
    v_manifest_path text;
    v_lease_expires_at timestamptz;
    expired record;
BEGIN
    IF length(trim(COALESCE(p_owner, ''))) = 0 THEN
        RAISE EXCEPTION 'restore drill lease owner is required';
    END IF;
    IF p_lease_seconds < 60 OR p_lease_seconds > 86400 THEN
        RAISE EXCEPTION 'restore drill lease must be between 60 and 86400 seconds';
    END IF;

    FOR expired IN
        UPDATE restore_drill_runs AS active_run
        SET status = 'failed',
            completed_at = now(),
            error = 'Restore drill lease expired before completion'
        WHERE active_run.status = 'running'
          AND active_run.lease_expires_at <= now()
        RETURNING active_run.run_id, active_run.owner,
                  active_run.lease_expires_at
    LOOP
        INSERT INTO restore_drill_run_events(run_id, event_type, actor, details)
        VALUES (
            expired.run_id,
            'lease_expired',
            'restore-drill-coordinator',
            jsonb_build_object(
                'owner', expired.owner,
                'lease_expires_at', expired.lease_expires_at
            )
        );
    END LOOP;

    SELECT b.backup_id, b.backup_stamp, b.backup_set_hash, b.manifest_path
    INTO v_backup_id, v_backup_stamp, v_backup_set_hash, v_manifest_path
    FROM backup_runs AS b
    WHERE b.status = 'completed'
      AND b.integrity_verified
      AND b.database_verified
      AND b.minio_verified
      AND b.knowledge_verified
      AND b.backup_set_hash IS NOT NULL
      AND b.manifest_path IS NOT NULL
    ORDER BY b.completed_at DESC, b.started_at DESC
    LIMIT 1;
    IF v_backup_id IS NULL THEN
        RAISE EXCEPTION 'no eligible canonical backup is available for restore drill';
    END IF;
    IF v_manifest_path <> '/backups/backup-set-' || v_backup_stamp || '.json' THEN
        RAISE EXCEPTION 'canonical backup manifest path is invalid';
    END IF;

    v_run_id := gen_random_uuid();
    v_lease_token := gen_random_uuid();
    v_lease_expires_at := now() + (p_lease_seconds * interval '1 second');
    BEGIN
        INSERT INTO restore_drill_runs(
            run_id, backup_id, backup_set_hash, status, owner,
            lease_token, lease_expires_at
        ) VALUES (
            v_run_id, v_backup_id, v_backup_set_hash, 'running', trim(p_owner),
            v_lease_token, v_lease_expires_at
        );
    EXCEPTION WHEN unique_violation THEN
        RAISE EXCEPTION 'another restore drill lease is already active';
    END;
    INSERT INTO restore_drill_run_events(run_id, event_type, actor, details)
    VALUES (
        v_run_id,
        'acquired',
        trim(p_owner),
        jsonb_build_object(
            'backup_id', v_backup_id,
            'backup_set_hash', v_backup_set_hash,
            'lease_expires_at', v_lease_expires_at
        )
    );
    RETURN QUERY SELECT
        v_run_id,
        v_lease_token,
        v_backup_id,
        v_backup_stamp,
        v_backup_set_hash,
        'backup-set-' || v_backup_stamp || '.json',
        v_lease_expires_at;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION complete_restore_drill_run(
    p_run_id uuid,
    p_lease_token uuid,
    p_report_content_hash text,
    p_verification_id uuid,
    p_actor text
)
RETURNS text AS $$
DECLARE
    current_run restore_drill_runs%ROWTYPE;
    verification_matches boolean;
BEGIN
    IF length(trim(COALESCE(p_actor, ''))) = 0 THEN
        RAISE EXCEPTION 'restore drill completion actor is required';
    END IF;
    SELECT * INTO current_run
    FROM restore_drill_runs
    WHERE run_id = p_run_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'restore drill run is unknown';
    END IF;
    IF current_run.status <> 'running' THEN
        RAISE EXCEPTION 'restore drill run is not active';
    END IF;
    IF current_run.lease_token <> p_lease_token THEN
        RAISE EXCEPTION 'restore drill lease token does not match';
    END IF;
    IF current_run.lease_expires_at <= now() THEN
        UPDATE restore_drill_runs
        SET status = 'failed',
            completed_at = now(),
            error = 'Restore drill lease expired before completion'
        WHERE run_id = p_run_id;
        INSERT INTO restore_drill_run_events(run_id, event_type, actor, details)
        VALUES (
            p_run_id,
            'lease_expired',
            trim(p_actor),
            jsonb_build_object('lease_expires_at', current_run.lease_expires_at)
        );
        RETURN 'failed';
    END IF;
    IF p_report_content_hash !~ '^[0-9a-f]{64}$' THEN
        RAISE EXCEPTION 'restore drill report content hash is invalid';
    END IF;
    SELECT v.outcome = 'verified'
           AND v.backup_id = current_run.backup_id
           AND v.backup_set_hash = current_run.backup_set_hash
           AND v.content_hash = p_report_content_hash
    INTO verification_matches
    FROM backup_restore_verifications AS v
    WHERE v.verification_id = p_verification_id;
    IF verification_matches IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'restore verification does not match the leased backup and report';
    END IF;

    UPDATE restore_drill_runs
    SET status = 'completed',
        completed_at = now(),
        report_content_hash = p_report_content_hash,
        verification_id = p_verification_id
    WHERE run_id = p_run_id;
    INSERT INTO restore_drill_run_events(run_id, event_type, actor, details)
    VALUES (
        p_run_id,
        'completed',
        trim(p_actor),
        jsonb_build_object(
            'report_content_hash', p_report_content_hash,
            'verification_id', p_verification_id
        )
    );
    RETURN 'completed';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fail_restore_drill_run(
    p_run_id uuid,
    p_lease_token uuid,
    p_error text,
    p_actor text
)
RETURNS text AS $$
DECLARE
    current_run restore_drill_runs%ROWTYPE;
BEGIN
    IF length(trim(COALESCE(p_actor, ''))) = 0 THEN
        RAISE EXCEPTION 'restore drill failure actor is required';
    END IF;
    IF length(trim(COALESCE(p_error, ''))) = 0 THEN
        RAISE EXCEPTION 'restore drill failure reason is required';
    END IF;
    SELECT * INTO current_run
    FROM restore_drill_runs
    WHERE run_id = p_run_id
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'restore drill run is unknown';
    END IF;
    IF current_run.status <> 'running' THEN
        RAISE EXCEPTION 'restore drill run is not active';
    END IF;
    IF current_run.lease_token <> p_lease_token THEN
        RAISE EXCEPTION 'restore drill lease token does not match';
    END IF;

    UPDATE restore_drill_runs
    SET status = 'failed',
        completed_at = now(),
        error = left(trim(p_error), 2000)
    WHERE run_id = p_run_id;
    INSERT INTO restore_drill_run_events(run_id, event_type, actor, details)
    VALUES (
        p_run_id,
        'failed',
        trim(p_actor),
        jsonb_build_object('error', left(trim(p_error), 2000))
    );
    RETURN 'failed';
END;
$$ LANGUAGE plpgsql;

INSERT INTO storage_contract_registry(
    resource_name, resource_kind, owner_component, responsibility,
    source_of_truth, lifecycle_class, active, notes
) VALUES
(
    'restore_drill_runs',
    'postgres_table',
    'operations-backup',
    'Exclusive restore-drill lease and operational run coordination',
    false,
    'operational_staging',
    true,
    'Phase 1F-B; PostgreSQL coordinates one active isolated drill'
),
(
    'restore_drill_run_events',
    'postgres_table',
    'operations-backup',
    'Append-only restore-drill lifecycle audit events',
    true,
    'immutable_ledger',
    true,
    'Phase 1F-B; events do not replace signed restore evidence'
)
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
