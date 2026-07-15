CREATE TABLE IF NOT EXISTS workspace_users (
    user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text NOT NULL UNIQUE,
    display_name text NOT NULL,
    password_hash text NOT NULL,
    password_salt text NOT NULL,
    password_iterations integer NOT NULL CHECK (password_iterations >= 100000),
    roles text[] NOT NULL CHECK (cardinality(roles) > 0),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
    failed_attempts integer NOT NULL DEFAULT 0,
    locked_until timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspace_sessions (
    session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES workspace_users(user_id) ON DELETE CASCADE,
    token_hash text NOT NULL UNIQUE,
    csrf_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    user_agent_hash text
);
CREATE INDEX IF NOT EXISTS workspace_sessions_active_idx
    ON workspace_sessions(token_hash,expires_at) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS authentication_events (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text,
    event_type text NOT NULL CHECK (event_type IN
        ('login_succeeded','login_failed','logout','session_rejected','user_created')),
    occurred_at timestamptz NOT NULL DEFAULT now(),
    details jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS authentication_events_time_idx
    ON authentication_events(occurred_at DESC);

INSERT INTO storage_contract_registry(
    resource_name,resource_kind,owner_component,responsibility,source_of_truth,
    lifecycle_class,active,notes
) VALUES
    ('workspace_users','postgres_table','product-auth','Human identities and password hashes',true,'canonical',true,'PRODUCT-001F'),
    ('workspace_sessions','postgres_table','product-auth','Revocable browser sessions',true,'operational_staging',true,'PRODUCT-001F'),
    ('authentication_events','postgres_table','product-auth','Authentication security audit',true,'immutable_ledger',true,'PRODUCT-001F')
ON CONFLICT(resource_name) DO UPDATE SET active=true,updated_at=now();
