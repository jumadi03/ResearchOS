[CmdletBinding()]
param(
    [string]$HostName = "76.13.20.211",
    [string]$RemoteUser = "ubuntu",
    [string]$KeyPath = "$HOME\.ssh\researchos_hostinger_ed25519",
    [string]$DestinationRoot = "D:\ResearchOS\Backups\Hostinger",
    [int]$RetentionDays = 30,
    [int]$MaximumBackupAgeHours = 36
)

$ErrorActionPreference = "Stop"
$container = "researchos-backup-1"

function Assert-SafeChildPath {
    param([string]$Root, [string]$Candidate)
    $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $candidateFull = [IO.Path]::GetFullPath($Candidate)
    if (-not $candidateFull.StartsWith("$rootFull\", [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path escapes the configured backup root: $candidateFull"
    }
}

function Invoke-Ssh {
    param([string[]]$RemoteArguments)
    & ssh -i $KeyPath "$RemoteUser@$HostName" @RemoteArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Remote backup command failed"
    }
}

function Copy-RemoteFile {
    param([string]$Stamp, [string]$FileName, [string]$Destination)
    if ($Stamp -notmatch '^\d{8}T\d{6}Z$' -or $FileName -notmatch '^[A-Za-z0-9._-]+$') {
        throw "Unsafe backup component name"
    }
    $exportRoot = "/home/$RemoteUser/researchos-offsite-export/$Stamp"
    Invoke-Ssh @("mkdir", "-p", $exportRoot)
    Invoke-Ssh @(
        "sudo", "docker", "cp",
        "${container}:/backups/$FileName",
        "$exportRoot/$FileName"
    )
    Invoke-Ssh @(
        "sudo", "chown",
        "${RemoteUser}:${RemoteUser}",
        "$exportRoot/$FileName"
    )
    & scp -i $KeyPath "${RemoteUser}@${HostName}:$exportRoot/$FileName" $Destination
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to copy $FileName from Hostinger"
    }
}

if (-not (Test-Path -LiteralPath $KeyPath -PathType Leaf)) {
    throw "ResearchOS Hostinger SSH key was not found: $KeyPath"
}

$rootFull = [IO.Path]::GetFullPath($DestinationRoot)
New-Item -ItemType Directory -Force -Path $rootFull | Out-Null

$manifestNames = @(
    & ssh -i $KeyPath "$RemoteUser@$HostName" sudo docker exec $container `
        find /backups -maxdepth 1 -type f -name 'backup-set-*.json' -print
)
if ($LASTEXITCODE -ne 0 -or $manifestNames.Count -eq 0) {
    throw "No completed Hostinger backup manifest is available"
}
$manifestName = $manifestNames |
    ForEach-Object { [IO.Path]::GetFileName($_.Trim()) } |
    Sort-Object |
    Select-Object -Last 1
if ($manifestName -notmatch '^backup-set-(\d{8}T\d{6}Z)\.json$') {
    throw "Unexpected backup manifest name: $manifestName"
}
$stamp = $Matches[1]
$backupTime = [DateTime]::ParseExact(
    $stamp,
    "yyyyMMddTHHmmssZ",
    [Globalization.CultureInfo]::InvariantCulture,
    [Globalization.DateTimeStyles]::AssumeUniversal -bor
        [Globalization.DateTimeStyles]::AdjustToUniversal
)
if (([DateTime]::UtcNow - $backupTime).TotalHours -gt $MaximumBackupAgeHours) {
    throw "Latest completed Hostinger backup is older than $MaximumBackupAgeHours hours"
}
$finalDirectory = Join-Path $rootFull $stamp
$partialDirectory = Join-Path $rootFull ".partial-$stamp"
Assert-SafeChildPath $rootFull $finalDirectory
Assert-SafeChildPath $rootFull $partialDirectory

if (Test-Path -LiteralPath $finalDirectory -PathType Container) {
    Write-Output "offsite-backup=passed stamp=$stamp status=already-present"
    exit 0
}
if (Test-Path -LiteralPath $partialDirectory) {
    Remove-Item -LiteralPath $partialDirectory -Recurse -Force
}
New-Item -ItemType Directory -Path $partialDirectory | Out-Null

try {
    Copy-RemoteFile $stamp $manifestName (Join-Path $partialDirectory $manifestName)
    Copy-RemoteFile $stamp "$manifestName.sha256" (
        Join-Path $partialDirectory "$manifestName.sha256"
    )
    $manifestPath = Join-Path $partialDirectory $manifestName
    $manifestSidecar = Join-Path $partialDirectory "$manifestName.sha256"
    $expectedManifestHash = (
        (Get-Content -LiteralPath $manifestSidecar -Raw).Trim() -split '\s+'
    )[0].ToLowerInvariant()
    $actualManifestHash = (
        Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    if ($expectedManifestHash -ne $actualManifestHash) {
        throw "Backup manifest checksum mismatch"
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    foreach ($component in $manifest.components) {
        $fileName = [string]$component.file
        $componentPath = Join-Path $partialDirectory $fileName
        $sidecarPath = "$componentPath.sha256"
        Copy-RemoteFile $stamp $fileName $componentPath
        Copy-RemoteFile $stamp "$fileName.sha256" $sidecarPath
        $actualHash = (
            Get-FileHash -LiteralPath $componentPath -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        $sidecarHash = (
            (Get-Content -LiteralPath $sidecarPath -Raw).Trim() -split '\s+'
        )[0].ToLowerInvariant()
        if (
            $actualHash -ne ([string]$component.sha256).ToLowerInvariant() -or
            $actualHash -ne $sidecarHash
        ) {
            throw "Checksum mismatch for $fileName"
        }
    }

    Move-Item -LiteralPath $partialDirectory -Destination $finalDirectory
    Invoke-Ssh @(
        "rm", "-rf",
        "/home/$RemoteUser/researchos-offsite-export/$stamp"
    )
} catch {
    if (Test-Path -LiteralPath $partialDirectory) {
        Assert-SafeChildPath $rootFull $partialDirectory
        Remove-Item -LiteralPath $partialDirectory -Recurse -Force
    }
    throw
}

$cutoff = (Get-Date).AddDays(-$RetentionDays)
Get-ChildItem -LiteralPath $rootFull -Directory |
    Where-Object {
        $_.Name -match '^\d{8}T\d{6}Z$' -and $_.LastWriteTime -lt $cutoff
    } |
    ForEach-Object {
        Assert-SafeChildPath $rootFull $_.FullName
        Remove-Item -LiteralPath $_.FullName -Recurse -Force
    }

Write-Output "offsite-backup=passed stamp=$stamp status=copied-and-verified"
