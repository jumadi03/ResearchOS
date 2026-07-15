ALTER TABLE authentication_events DROP CONSTRAINT IF EXISTS authentication_events_event_type_check;
ALTER TABLE authentication_events ADD CONSTRAINT authentication_events_event_type_check
    CHECK (event_type IN ('login_succeeded','login_failed','logout','session_rejected',
                          'user_created','user_active','user_disabled','sessions_revoked'));

CREATE TABLE IF NOT EXISTS backup_runs (
    backup_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_stamp text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('running','completed','failed')),
    database_path text,
    minio_path text,
    knowledge_path text,
    database_verified boolean NOT NULL DEFAULT false,
    minio_verified boolean NOT NULL DEFAULT false,
    knowledge_verified boolean NOT NULL DEFAULT false,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    error text
);

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,source_of_truth,
    lifecycle_class,active,notes
) VALUES ('backup_runs','postgres_table','operations-backup',
          'Verified backup execution ledger',true,'immutable_ledger',true,'PRODUCT-001G')
ON CONFLICT(resource_name) DO UPDATE SET active=true,updated_at=now();
