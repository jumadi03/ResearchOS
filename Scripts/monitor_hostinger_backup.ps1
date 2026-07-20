[CmdletBinding()]
param(
    [string]$HostName = "76.13.20.211",
    [string]$RemoteUser = "ubuntu",
    [string]$KeyPath = "$HOME\.ssh\researchos_hostinger_ed25519",
    [string]$RepositoryRoot = "D:\ResearchOS",
    [string]$OperationalStateRoot = "",
    [int]$MaximumMonitorAgeMinutes = 5,
    [switch]$SuppressInteractiveNotification
)

$ErrorActionPreference = "Stop"
$backupRoot = Join-Path $RepositoryRoot "Backups\Hostinger"
if (-not $OperationalStateRoot) {
    $OperationalStateRoot = $backupRoot
}
$alertRoot = Join-Path $OperationalStateRoot "alerts"
$statusRoot = Join-Path $OperationalStateRoot "status"
$pullScript = Join-Path $RepositoryRoot "Scripts\pull_hostinger_backup.ps1"
$attestationScript = Join-Path $RepositoryRoot "Scripts\register_local_backup_attestation.ps1"

function Write-AtomicJson {
    param([string]$Path, [hashtable]$Payload)
    $directory = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $temporary = "$Path.partial"
    $Payload | ConvertTo-Json -Depth 8 |
        Set-Content -LiteralPath $temporary -Encoding UTF8
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

try {
    if (-not (Test-Path -LiteralPath $pullScript -PathType Leaf)) {
        throw "Offsite backup pull script is missing"
    }
    $rawState = & ssh -i $KeyPath "$RemoteUser@$HostName" sudo docker exec `
        researchos-monitor-1 cat /state/health.json
    if ($LASTEXITCODE -ne 0) {
        throw "Hostinger health monitor is unreachable"
    }
    $monitorState = ($rawState -join [Environment]::NewLine) | ConvertFrom-Json
    if ($monitorState.status -ne "passed") {
        throw "Hostinger health monitor reports failure"
    }
    $checkedAt = [DateTimeOffset]::Parse([string]$monitorState.checked_at)
    if (
        ([DateTimeOffset]::UtcNow - $checkedAt).TotalMinutes -gt
        $MaximumMonitorAgeMinutes
    ) {
        throw "Hostinger health monitor state is stale"
    }
    $databaseCheck = $monitorState.checks |
        Where-Object { $_.name -eq "postgresql" } |
        Select-Object -First 1
    if (-not $databaseCheck) {
        throw "Hostinger health monitor lacks the PostgreSQL check"
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $pullScript `
        -HostName $HostName -RemoteUser $RemoteUser -KeyPath $KeyPath `
        -DestinationRoot $backupRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Offsite backup pull or checksum verification failed"
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $attestationScript `
        -HostName $HostName -RemoteUser $RemoteUser -KeyPath $KeyPath `
        -BackupRoot $backupRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Local backup attestation failed"
    }

    $now = [DateTimeOffset]::UtcNow
    Write-AtomicJson (Join-Path $statusRoot "latest.json") @{
        schema_version = "1.0"
        checked_at = $now.ToString("o")
        status = "passed"
        monitor_checked_at = $checkedAt.ToString("o")
        monitor_schema_version = $databaseCheck.schema_version
        canonical_object_count = $databaseCheck.canonical_object_count
    }
    Write-Output "hostinger-backup-monitor=passed"
    exit 0
} catch {
    $now = [DateTimeOffset]::UtcNow
    $safeMessage = $_.Exception.Message
    $stamp = $now.ToString("yyyyMMddTHHmmssZ")
    $alert = @{
        schema_version = "1.0"
        detected_at = $now.ToString("o")
        status = "failed"
        component = "hostinger-backup-monitor"
        message = $safeMessage
    }
    Write-AtomicJson (Join-Path $alertRoot "alert-$stamp.json") $alert
    Write-AtomicJson (Join-Path $alertRoot "latest.json") $alert
    try {
        if ($SuppressInteractiveNotification) {
            throw "Interactive notification suppressed"
        }
        & msg.exe $env:USERNAME (
            "ResearchOS: backup atau monitor Hostinger gagal. " +
            "Buka D:\ResearchOS\Backups\Hostinger\alerts\latest.json"
        ) 2>$null
    } catch {
        # The durable alert file and failed task result remain authoritative.
    }
    Write-Error $safeMessage
    exit 1
}
