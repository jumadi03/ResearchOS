[CmdletBinding()]
param(
    [string]$DriveLetter = "E",
    [string]$ExpectedLabel = "PIRANG 02",
    [string]$Source = ""
)

$ErrorActionPreference = "Stop"
$managedStage = $false
$drive = Get-Volume -DriveLetter $DriveLetter
if ($drive.DriveType -ne "Removable") {
    throw "Target drive is not removable: ${DriveLetter}:"
}
if ($drive.FileSystemLabel -ne $ExpectedLabel) {
    throw "USB label mismatch; expected '$ExpectedLabel'"
}
if ($drive.HealthStatus -ne "Healthy") {
    throw "USB volume is not healthy"
}
if (-not $Source) {
    if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) {
        throw "Docker Desktop command is unavailable"
    }
    $stageRoot = "D:\ResearchOS\AI-Gateway\.tmp\usb-backup-staging"
    New-Item -ItemType Directory -Force -Path $stageRoot | Out-Null
    $Source = Join-Path $stageRoot ([guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $Source | Out-Null
    docker cp "researchos-backup-1:/backups/." $Source
    if ($LASTEXITCODE -ne 0) {
        throw "Canonical backup export from Docker failed"
    }
    $managedStage = $true
}
if (
    -not (Test-Path -LiteralPath $Source -PathType Container) -or
    -not (Get-ChildItem -LiteralPath $Source -Filter "backup-set-*.json")
) {
    throw "Canonical backup staging source is missing or incomplete"
}

$restic = Get-Command restic.exe -ErrorAction SilentlyContinue
if (-not $restic) {
    $restic = Get-Item -LiteralPath (
        "C:\Users\ROG\AppData\Local\Programs\ResearchOS\restic\restic.exe"
    )
}
$resticPath = if ($restic.Source) {
    $restic.Source
} else {
    $restic.FullName
}
if (-not (Test-Path -LiteralPath $resticPath -PathType Leaf)) {
    throw "Restic executable path is invalid"
}

$repository = "${DriveLetter}:\ResearchOS-Encrypted-Backup"
$config = Join-Path $repository "config"
$password = Read-Host "Restic encryption password" -AsSecureString
$credential = [System.Net.NetworkCredential]::new("", $password)
$env:RESTIC_PASSWORD = $credential.Password
if (-not $env:RESTIC_PASSWORD) {
    throw "Encryption password cannot be empty"
}

try {
    if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
        $confirmation = Read-Host "Repeat encryption password" -AsSecureString
        $confirmationCredential = [System.Net.NetworkCredential]::new(
            "", $confirmation
        )
        if ($env:RESTIC_PASSWORD -cne $confirmationCredential.Password) {
            throw "Encryption passwords do not match"
        }
        New-Item -ItemType Directory -Force -Path $repository | Out-Null
        & $resticPath -r $repository init
        if ($LASTEXITCODE -ne 0) {
            throw "Restic repository initialization failed"
        }
    }

    & $resticPath -r $repository backup $Source `
        --host "researchos-windows" `
        --tag "canonical-usb" `
        --tag "restore-verified-source"
    if ($LASTEXITCODE -ne 0) {
        throw "Encrypted USB backup failed"
    }

    & $resticPath -r $repository check --read-data
    if ($LASTEXITCODE -ne 0) {
        throw "Encrypted USB repository verification failed"
    }

    & $resticPath -r $repository forget `
        --host "researchos-windows" `
        --tag "canonical-usb" `
        --group-by "host,tags" `
        --keep-last 8 `
        --keep-weekly 12 `
        --keep-monthly 12 `
        --prune
    if ($LASTEXITCODE -ne 0) {
        throw "Encrypted USB retention and prune failed"
    }

    & $resticPath -r $repository check
    if ($LASTEXITCODE -ne 0) {
        throw "Post-retention repository verification failed"
    }

    $snapshots = & $resticPath -r $repository snapshots `
        --host "researchos-windows" `
        --tag "canonical-usb" `
        --json | ConvertFrom-Json
    $snapshot = @($snapshots) |
        Sort-Object { [datetime]$_.time } -Descending |
        Select-Object -First 1
    [pscustomobject]@{
        status = "completed"
        repository = $repository
        snapshot_id = [string]$snapshot.short_id
        verified = $true
        source = $Source
    } | ConvertTo-Json -Compress
}
finally {
    Remove-Item Env:\RESTIC_PASSWORD -ErrorAction SilentlyContinue
    $credential = $null
    $password = $null
    if ($managedStage -and (Test-Path -LiteralPath $Source)) {
        $resolved = (Resolve-Path -LiteralPath $Source).Path
        $allowed = "D:\ResearchOS\AI-Gateway\.tmp\usb-backup-staging\"
        if (
            -not $resolved.StartsWith(
                $allowed, [System.StringComparison]::OrdinalIgnoreCase
            )
        ) {
            throw "Managed staging cleanup target escaped its fixed root"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
