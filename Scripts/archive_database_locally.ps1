[CmdletBinding()]
param(
    [string]$BackupRoot = "D:\ResearchOS\Backups\Hostinger",
    [string]$BackupStamp,
    [string]$PostgresUser = "researchos"
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repositoryRoot "deploy\compose.yaml"
$environmentFile = Join-Path $repositoryRoot "deploy\stack.env"

if ($BackupStamp -and $BackupStamp -notmatch '^\d{8}T\d{6}Z$') {
    throw "BackupStamp must use YYYYMMDDTHHMMSSZ"
}

$generations = Get-ChildItem -LiteralPath $BackupRoot -Directory |
    Where-Object { $_.Name -match '^\d{8}T\d{6}Z$' } |
    Sort-Object Name -Descending
if ($BackupStamp) {
    $generation = $generations | Where-Object Name -eq $BackupStamp |
        Select-Object -First 1
} else {
    $generation = $generations | Select-Object -First 1
}
if (-not $generation) { throw "Requested local backup generation is unavailable" }

$stamp = $generation.Name
$manifestPath = Join-Path $generation.FullName "backup-set-$stamp.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.backup_stamp -ne $stamp) { throw "Backup manifest stamp mismatch" }

$component = @($manifest.components | Where-Object name -eq "postgresql")
if ($component.Count -ne 1) { throw "Backup must contain exactly one PostgreSQL component" }
$file = [string]$component[0].file
$expectedHash = ([string]$component[0].sha256).ToLowerInvariant()
if ($file -notmatch '^researchos-\d{8}T\d{6}Z\.dump$' -or
    $expectedHash -notmatch '^[0-9a-f]{64}$') {
    throw "Unsafe PostgreSQL backup metadata"
}
$dumpPath = Join-Path $generation.FullName $file
$actualHash = (Get-FileHash -LiteralPath $dumpPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $expectedHash) { throw "PostgreSQL dump checksum mismatch" }

& docker compose --env-file $environmentFile -f $composeFile `
    --profile local-archive up -d --wait archive-postgres
if ($LASTEXITCODE -ne 0) { throw "Local archive PostgreSQL did not start" }

$container = "researchos-archive-postgres-1"
$database = "researchos_archive_$($stamp.ToLowerInvariant())"
if ($database -notmatch '^researchos_archive_\d{8}t\d{6}z$') {
    throw "Unsafe archive database identity"
}

$catalogSql = @'
CREATE TABLE IF NOT EXISTS local_archive_generations (
    database_name text PRIMARY KEY CHECK (
        database_name ~ '^researchos_archive_[0-9]{8}t[0-9]{6}z$'
    ),
    backup_stamp text NOT NULL UNIQUE CHECK (
        backup_stamp ~ '^[0-9]{8}T[0-9]{6}Z$'
    ),
    dump_sha256 text NOT NULL CHECK (dump_sha256 ~ '^[0-9a-f]{64}$'),
    schema_version integer NOT NULL CHECK (schema_version > 0),
    canonical_object_count bigint NOT NULL CHECK (canonical_object_count >= 0),
    archived_at timestamptz NOT NULL DEFAULT now(),
    verification jsonb NOT NULL CHECK (jsonb_typeof(verification) = 'object')
);
CREATE OR REPLACE FUNCTION reject_local_archive_mutation()
RETURNS trigger LANGUAGE plpgsql AS $function$
BEGIN
    RAISE EXCEPTION 'local database archive ledger is immutable';
END;
$function$;
DROP TRIGGER IF EXISTS local_archive_generations_immutable
    ON local_archive_generations;
CREATE TRIGGER local_archive_generations_immutable
    BEFORE UPDATE OR DELETE ON local_archive_generations
    FOR EACH ROW EXECUTE FUNCTION reject_local_archive_mutation();

CREATE TABLE IF NOT EXISTS local_inactive_archive_items (
    item_id uuid PRIMARY KEY,
    item_kind text NOT NULL CHECK (
        item_kind IN ('legacy_github_bundle','stale_file')
    ),
    source_locator text NOT NULL,
    original_filename text NOT NULL CHECK (
        original_filename !~ '[\\/]' AND original_filename <> ''
    ),
    content_sha256 text NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    content_size bigint NOT NULL CHECK (content_size >= 0),
    content bytea NOT NULL,
    archived_reason text NOT NULL CHECK (archived_reason <> ''),
    archived_at timestamptz NOT NULL DEFAULT now(),
    metadata jsonb NOT NULL CHECK (jsonb_typeof(metadata) = 'object'),
    UNIQUE (item_kind, source_locator, content_sha256),
    CHECK (octet_length(content) = content_size)
);
CREATE TABLE IF NOT EXISTS local_inactive_archive_restores (
    restore_id uuid PRIMARY KEY,
    item_id uuid NOT NULL REFERENCES local_inactive_archive_items(item_id),
    restored_at timestamptz NOT NULL DEFAULT now(),
    destination text NOT NULL,
    restored_sha256 text NOT NULL CHECK (restored_sha256 ~ '^[0-9a-f]{64}$'),
    verification jsonb NOT NULL CHECK (jsonb_typeof(verification) = 'object')
);
DROP TRIGGER IF EXISTS local_inactive_archive_items_immutable
    ON local_inactive_archive_items;
CREATE TRIGGER local_inactive_archive_items_immutable
    BEFORE UPDATE OR DELETE ON local_inactive_archive_items
    FOR EACH ROW EXECUTE FUNCTION reject_local_archive_mutation();
DROP TRIGGER IF EXISTS local_inactive_archive_restores_immutable
    ON local_inactive_archive_restores;
CREATE TRIGGER local_inactive_archive_restores_immutable
    BEFORE UPDATE OR DELETE ON local_inactive_archive_restores
    FOR EACH ROW EXECUTE FUNCTION reject_local_archive_mutation();
'@
$catalogSql | & docker exec -i $container psql -v ON_ERROR_STOP=1 `
    -U $PostgresUser -d postgres
if ($LASTEXITCODE -ne 0) { throw "Could not initialize local archive catalog" }

$exists = & docker exec $container psql -At -U $PostgresUser -d postgres `
    -c "SELECT 1 FROM pg_database WHERE datname = '$database'"
if ($LASTEXITCODE -ne 0) { throw "Could not inspect local archive databases" }

if (-not $exists) {
    & docker exec $container createdb -U $PostgresUser $database
    if ($LASTEXITCODE -ne 0) { throw "Could not create local archive database" }
    try {
        & docker cp $dumpPath "${container}:/tmp/$file"
        if ($LASTEXITCODE -ne 0) { throw "Could not stage PostgreSQL archive dump" }
        & docker exec $container pg_restore --no-owner --no-privileges `
            -U $PostgresUser -d $database "/tmp/$file"
        if ($LASTEXITCODE -ne 0) { throw "Could not restore local database archive" }
    } catch {
        if ($database -match '^researchos_archive_\d{8}t\d{6}z$') {
            & docker exec $container dropdb -U $PostgresUser --if-exists $database
        }
        throw
    } finally {
        & docker exec $container rm -f "/tmp/$file" | Out-Null
    }
}

$schemaVersion = & docker exec $container psql -At -U $PostgresUser -d $database `
    -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
if ($LASTEXITCODE -ne 0 -or $schemaVersion -notmatch '^\d+$') {
    throw "Local archive schema verification failed"
}
$canonicalCount = & docker exec $container psql -At -U $PostgresUser -d $database `
    -c "SELECT COUNT(*) FROM canonical_objects"
if ($LASTEXITCODE -ne 0 -or $canonicalCount -notmatch '^\d+$') {
    throw "Local archive canonical-object verification failed"
}

$existing = & docker exec $container psql -At -U $PostgresUser -d postgres `
    -c "SELECT dump_sha256 FROM local_archive_generations WHERE database_name = '$database'"
if ($existing -and $existing -ne $expectedHash) {
    throw "Existing archive catalog hash conflicts with verified dump"
}
if (-not $existing) {
    $insert = @"
INSERT INTO local_archive_generations(
    database_name,backup_stamp,dump_sha256,schema_version,
    canonical_object_count,verification
) VALUES (
    '$database','$stamp','$expectedHash',$schemaVersion,$canonicalCount,
    '{"checksum_verified":true,"read_back_verified":true}'::jsonb
);
"@
    $insert | & docker exec -i $container psql -v ON_ERROR_STOP=1 `
        -U $PostgresUser -d postgres
    if ($LASTEXITCODE -ne 0) { throw "Could not admit local archive generation" }
}

Write-Output (
    "local-database-archive=passed database=$database stamp=$stamp " +
    "schema=$schemaVersion canonical_objects=$canonicalCount sha256=$expectedHash"
)
