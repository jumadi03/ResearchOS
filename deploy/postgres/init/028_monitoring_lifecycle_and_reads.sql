CREATE TABLE IF NOT EXISTS scientific_source_watch_transitions (
    transition_id text PRIMARY KEY,
    watch_id text NOT NULL REFERENCES scientific_source_watches(watch_id),
    from_status text NOT NULL CHECK(from_status IN ('active','paused')),
    to_status text NOT NULL CHECK(to_status IN ('active','paused')),
    actor_id text NOT NULL,
    rationale text NOT NULL CHECK(length(trim(rationale)) > 0),
    occurred_at timestamptz NOT NULL,
    next_run_at timestamptz,
    CHECK(from_status <> to_status),
    CHECK(to_status <> 'active' OR next_run_at IS NOT NULL)
);

DROP TRIGGER IF EXISTS scientific_source_watch_transitions_immutable
    ON scientific_source_watch_transitions;
CREATE TRIGGER scientific_source_watch_transitions_immutable
    BEFORE UPDATE OR DELETE ON scientific_source_watch_transitions
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

CREATE INDEX IF NOT EXISTS scientific_monitoring_runs_watch_schedule_idx
    ON scientific_monitoring_runs(watch_id,scheduled_at DESC);
CREATE INDEX IF NOT EXISTS scientific_changes_monitoring_run_idx
    ON scientific_changes(monitoring_run_id,change_kind);

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES (
    'scientific_source_watch_transitions','postgres_table',
    'Continuous Monitoring',
    'Actor-attributed pause and resume decisions with rationale',
    true,'immutable_ledger',true,
    'Expired status remains system-derived and terminal'
) ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
