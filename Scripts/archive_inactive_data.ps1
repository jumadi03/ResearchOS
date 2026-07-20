[CmdletBinding(DefaultParameterSetName = "Files")]
param(
    [Parameter(Mandatory, ParameterSetName = "Files")]
    [string[]]$Path,
    [Parameter(Mandatory, ParameterSetName = "GitHub")]
    [switch]$LegacyGitHubSnapshot,
    [Parameter(Mandatory)]
    [string]$Reason
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$archiveScript = Join-Path $PSScriptRoot "archive_database_locally.ps1"
$container = "researchos-archive-postgres-1"
$postgresUser = "researchos"
$temporaryFiles = [System.Collections.Generic.List[string]]::new()

function Invoke-ArchiveSql {
    param([Parameter(Mandatory)][string]$Sql)
    $Sql | & docker exec -i $container psql -v ON_ERROR_STOP=1 `
        -U $postgresUser -d postgres
    if ($LASTEXITCODE -ne 0) { throw "Local inactive archive operation failed" }
}

function Add-InactiveItem {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string]$Kind,
        [Parameter(Mandatory)][string]$SourceLocator,
        [Parameter(Mandatory)][hashtable]$Metadata
    )
    $resolved = (Resolve-Path -LiteralPath $FilePath).Path
    $fileInfo = Get-Item -LiteralPath $resolved
    if (-not $fileInfo.PSIsContainer -and $fileInfo.Length -gt 104857600) {
        throw "Inactive archive item exceeds the 100 MiB safety limit"
    }
    if ($fileInfo.PSIsContainer) { throw "Only files can enter the inactive archive" }

    $hash = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
    $itemId = [guid]::NewGuid().ToString()
    $stageName = "$itemId.bin"
    $metadataPath = Join-Path ([System.IO.Path]::GetTempPath()) "$itemId.json"
    $payload = @{
        item_id = $itemId
        item_kind = $Kind
        source_locator = $SourceLocator
        original_filename = $fileInfo.Name
        content_sha256 = $hash
        content_size = $fileInfo.Length
        archived_reason = $Reason
        metadata = $Metadata
    } | ConvertTo-Json -Depth 10 -Compress
    [System.IO.File]::WriteAllText($metadataPath, $payload, [Text.UTF8Encoding]::new($false))
    try {
        & docker cp $resolved "${container}:/tmp/$stageName"
        if ($LASTEXITCODE -ne 0) { throw "Could not stage inactive archive content" }
        & docker cp $metadataPath "${container}:/tmp/$itemId.json"
        if ($LASTEXITCODE -ne 0) { throw "Could not stage inactive archive metadata" }
        $sql = @"
WITH p AS (
    SELECT pg_read_file('/tmp/$itemId.json')::jsonb AS value
), admitted AS (
    INSERT INTO local_inactive_archive_items(
        item_id,item_kind,source_locator,original_filename,content_sha256,
        content_size,content,archived_reason,metadata
    )
    SELECT
        (value->>'item_id')::uuid,value->>'item_kind',
        value->>'source_locator',value->>'original_filename',
        value->>'content_sha256',(value->>'content_size')::bigint,
        pg_read_binary_file('/tmp/$stageName'),value->>'archived_reason',
        value->'metadata'
    FROM p
    ON CONFLICT (item_kind,source_locator,content_sha256) DO NOTHING
    RETURNING item_id
)
SELECT item_id FROM admitted
UNION ALL
SELECT item_id FROM local_inactive_archive_items,p
WHERE item_kind = p.value->>'item_kind'
  AND source_locator = p.value->>'source_locator'
  AND content_sha256 = p.value->>'content_sha256'
LIMIT 1;
"@
        $result = $sql | & docker exec -i $container psql -At -v ON_ERROR_STOP=1 `
            -U $postgresUser -d postgres
        if ($LASTEXITCODE -ne 0 -or $result -notmatch '^[0-9a-f-]{36}$') {
            throw "Inactive archive admission did not return a valid identity"
        }
        Write-Output "inactive-archive=passed item_id=$result kind=$Kind sha256=$hash source=$SourceLocator"
    } finally {
        Remove-Item -LiteralPath $metadataPath -Force -ErrorAction SilentlyContinue
        & docker exec $container rm -f "/tmp/$stageName" "/tmp/$itemId.json" |
            Out-Null
    }
}

& $archiveScript | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Local archive database is unavailable" }

try {
    if ($LegacyGitHubSnapshot) {
        $stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
        $bundle = Join-Path ([System.IO.Path]::GetTempPath()) "legacy-github-$stamp.bundle"
        $temporaryFiles.Add($bundle)
        $refs = @(& git for-each-ref --format='%(refname)' refs/remotes/legacy-github/)
        if ($LASTEXITCODE -ne 0 -or $refs.Count -eq 0) {
            throw "No local legacy-github references are available"
        }
        & git bundle create $bundle @refs
        if ($LASTEXITCODE -ne 0) { throw "Could not create the legacy GitHub bundle" }
        & git bundle verify $bundle | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "Legacy GitHub bundle verification failed" }
        $tips = @(& git for-each-ref --format='%(refname)|%(objectname)|%(subject)' `
            refs/remotes/legacy-github/)
        Add-InactiveItem -FilePath $bundle -Kind "legacy_github_bundle" `
            -SourceLocator "legacy-github://remote-tracking-refs" `
            -Metadata @{
                captured_at = $stamp
                reference_count = $refs.Count
                references = $tips
                active_source = $false
            }
    } else {
        foreach ($candidate in $Path) {
            $resolved = (Resolve-Path -LiteralPath $candidate).Path
            $rootPrefix = $repositoryRoot.TrimEnd('\') + '\'
            if (-not $resolved.StartsWith(
                $rootPrefix, [StringComparison]::OrdinalIgnoreCase
            )) {
                throw "Stale files must be inside the ResearchOS workspace"
            }
            $relative = $resolved.Substring($rootPrefix.Length)
            Add-InactiveItem -FilePath $resolved -Kind "stale_file" `
                -SourceLocator "workspace://$($relative.Replace('\','/'))" `
                -Metadata @{
                    archived_from = $relative.Replace('\','/')
                    active_source = $false
                }
        }
    }
} finally {
    foreach ($temporary in $temporaryFiles) {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}
