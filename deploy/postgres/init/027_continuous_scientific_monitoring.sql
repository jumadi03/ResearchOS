CREATE TABLE IF NOT EXISTS scientific_source_watches (
    watch_id text PRIMARY KEY,
    project_id text NOT NULL,
    discovery_contract_id text NOT NULL,
    research_question_id text NOT NULL,
    search_plan_id text NOT NULL,
    cadence_minutes integer NOT NULL CHECK(cadence_minutes >= 15),
    owner_id text NOT NULL,
    human_review_policy text NOT NULL,
    created_at timestamptz NOT NULL,
    maximum_runs integer CHECK(maximum_runs > 0),
    ends_at timestamptz,
    definition_hash text NOT NULL CHECK(length(definition_hash) = 64),
    schema_version text NOT NULL
);

CREATE TABLE IF NOT EXISTS scientific_source_watch_state (
    watch_id text PRIMARY KEY REFERENCES scientific_source_watches(watch_id),
    status text NOT NULL CHECK(status IN ('active','paused','expired')),
    next_run_at timestamptz NOT NULL,
    completed_runs integer NOT NULL DEFAULT 0 CHECK(completed_runs >= 0),
    baseline_discovery_run jsonb NOT NULL,
    baseline_hash text NOT NULL CHECK(length(baseline_hash) = 64),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scientific_monitoring_runs (
    monitoring_run_id text PRIMARY KEY,
    watch_id text NOT NULL REFERENCES scientific_source_watches(watch_id),
    scheduled_at timestamptz NOT NULL,
    started_at timestamptz NOT NULL,
    completed_at timestamptz NOT NULL,
    previous_discovery_run_id text NOT NULL,
    current_discovery_run_id text NOT NULL,
    provider_failures jsonb NOT NULL,
    stopping_reason text NOT NULL CHECK(
        stopping_reason IN ('complete','partial_provider_failure')
    ),
    manifest_hash text NOT NULL CHECK(length(manifest_hash) = 64),
    schema_version text NOT NULL,
    UNIQUE(watch_id,scheduled_at)
);

CREATE TABLE IF NOT EXISTS scientific_changes (
    change_id text PRIMARY KEY,
    monitoring_run_id text NOT NULL
        REFERENCES scientific_monitoring_runs(monitoring_run_id),
    change_kind text NOT NULL CHECK(change_kind IN (
        'new_candidate','metadata_changed','citation_changed','corrected',
        'retracted','unavailable','provider_failure'
    )),
    record_key text NOT NULL,
    provider text,
    before_hash text CHECK(before_hash IS NULL OR length(before_hash) = 64),
    after_hash text CHECK(after_hash IS NULL OR length(after_hash) = 64),
    details jsonb NOT NULL,
    UNIQUE(monitoring_run_id,change_kind,record_key,provider)
);

CREATE TABLE IF NOT EXISTS scientific_change_acknowledgements (
    acknowledgement_id text PRIMARY KEY,
    change_id text NOT NULL REFERENCES scientific_changes(change_id),
    actor_id text NOT NULL,
    rationale text NOT NULL CHECK(length(trim(rationale)) > 0),
    occurred_at timestamptz NOT NULL
);

ALTER TABLE background_jobs
    DROP CONSTRAINT IF EXISTS background_jobs_job_type_check;
ALTER TABLE background_jobs
    ADD CONSTRAINT background_jobs_job_type_check CHECK(job_type IN (
        'parse_document','normalize_metadata','index_embedding',
        'run_source_watch'
    ));

DROP TRIGGER IF EXISTS scientific_source_watches_immutable
    ON scientific_source_watches;
CREATE TRIGGER scientific_source_watches_immutable
    BEFORE UPDATE OR DELETE ON scientific_source_watches
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

DROP TRIGGER IF EXISTS scientific_monitoring_runs_immutable
    ON scientific_monitoring_runs;
CREATE TRIGGER scientific_monitoring_runs_immutable
    BEFORE UPDATE OR DELETE ON scientific_monitoring_runs
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

DROP TRIGGER IF EXISTS scientific_changes_immutable ON scientific_changes;
CREATE TRIGGER scientific_changes_immutable
    BEFORE UPDATE OR DELETE ON scientific_changes
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

DROP TRIGGER IF EXISTS scientific_change_acknowledgements_immutable
    ON scientific_change_acknowledgements;
CREATE TRIGGER scientific_change_acknowledgements_immutable
    BEFORE UPDATE OR DELETE ON scientific_change_acknowledgements
    FOR EACH ROW EXECUTE FUNCTION reject_ledger_mutation();

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,
    source_of_truth,lifecycle_class,active,notes
) VALUES
('scientific_source_watches','postgres_table','Continuous Monitoring',
 'Immutable contract-bound watch definitions',true,'immutable_ledger',true,
 'Monitoring may not expand the approved discovery scope'),
('scientific_source_watch_state','postgres_table','Continuous Monitoring',
 'Mutable schedule state and latest verified discovery baseline',true,
 'canonical',true,'Only the resilient worker advances state'),
('scientific_monitoring_runs','postgres_table','Continuous Monitoring',
 'Immutable execution manifests and provider coverage',true,
 'immutable_ledger',true,'Partial provider failure remains explicit'),
('scientific_changes','postgres_table','Continuous Monitoring',
 'Candidate scientific changes without evidence admission',true,
 'immutable_ledger',true,'Changes return through normal human review'),
('scientific_change_acknowledgements','postgres_table','Continuous Monitoring',
 'Actor-attributed acknowledgement and rationale',true,
 'immutable_ledger',true,'Acknowledgement never changes evidence status')
ON CONFLICT(resource_name) DO UPDATE SET
    owner_component=excluded.owner_component,
    responsibility=excluded.responsibility,
    source_of_truth=excluded.source_of_truth,
    lifecycle_class=excluded.lifecycle_class,
    active=excluded.active,
    notes=excluded.notes,
    updated_at=now();
