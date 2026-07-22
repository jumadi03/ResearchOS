[CmdletBinding()]
param(
    [string]$HostName = "76.13.20.211",
    [string]$RemoteUser = "ubuntu",
    [string]$KeyPath = "$HOME\.ssh\researchos_hostinger_ed25519",
    [string]$BackupRoot = "D:\ResearchOS\Backups\Hostinger",
    [int]$RetentionDays = 30,
    [ValidateSet("Hostinger", "Local")]
    [string]$Target = "Hostinger"
)

$ErrorActionPreference = "Stop"
$directories = Get-ChildItem -LiteralPath $BackupRoot -Directory |
    Where-Object { $_.Name -match '^\d{8}T\d{6}Z$' } |
    Sort-Object Name -Descending
if (-not $directories) { throw "No local Hostinger backup is available" }
$directory = $directories[0]
$stamp = $directory.Name
$manifestPath = Join-Path $directory.FullName "backup-set-$stamp.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.backup_stamp -ne $stamp) { throw "Backup stamp mismatch" }

$allowed = @('postgresql','minio','knowledge','architecture','configuration','migration')
$values = @()
foreach ($component in $manifest.components) {
    $name = [string]$component.name
    $file = [string]$component.file
    $hash = ([string]$component.sha256).ToLowerInvariant()
    if ($name -notin $allowed -or $file -notmatch '^[A-Za-z0-9._-]+$' -or $hash -notmatch '^[0-9a-f]{64}$') {
        throw "Unsafe backup component metadata"
    }
    $path = Join-Path $directory.FullName $file
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $hash) { throw "Local checksum mismatch for $file" }
    $retention = [DateTime]::UtcNow.AddDays($RetentionDays).ToString('yyyy-MM-dd')
    $verified = [DateTimeOffset]::UtcNow.ToString('o')
    $values += "('$stamp','$name','hot','vps-backup:$stamp/$file','$hash','$verified','local-offsite-sync',NULL,'{`"checksum_verified`":true}'::jsonb)"
    $values += "('$stamp','$name','archived_local','hostinger-offsite:$stamp/$file','$hash','$verified','local-offsite-sync','$retention','{`"checksum_verified`":true}'::jsonb)"
}

$sql = @"
INSERT INTO storage_tier_attestations(
  backup_stamp,component_name,storage_tier,canonical_locator,content_sha256,
  verified_at,verifier,retention_until,evidence
) VALUES
$($values -join ",`n")
ON CONFLICT (backup_stamp,component_name,storage_tier,content_sha256) DO NOTHING;
"@
$temporary = Join-Path $env:TEMP "researchos-storage-tier-$stamp.sql"
$remote = "/home/$RemoteUser/researchos-storage-tier-$stamp.sql"
try {
    [IO.File]::WriteAllText(
        $temporary, $sql, (New-Object Text.UTF8Encoding($false))
    )
    if ($Target -eq "Local") {
        Get-Content -LiteralPath $temporary -Raw |
            & docker exec -i researchos-postgres-1 psql `
                -v ON_ERROR_STOP=1 -U researchos -d researchos
        if ($LASTEXITCODE -ne 0) {
            throw "Local storage attestation was rejected"
        }
        Write-Output (
            "storage-tier-attestation=passed target=local " +
            "stamp=$stamp components=$($manifest.components.Count)"
        )
        exit 0
    }
    & scp -i $KeyPath $temporary "${RemoteUser}@${HostName}:$remote"
    if ($LASTEXITCODE -ne 0) { throw "Could not upload storage attestation" }
    & ssh -i $KeyPath "$RemoteUser@$HostName" sudo docker cp $remote `
        researchos-postgres-1:/tmp/storage-tier.sql
    if ($LASTEXITCODE -ne 0) { throw "Could not stage storage attestation" }
    & ssh -i $KeyPath "$RemoteUser@$HostName" sudo docker exec `
        researchos-postgres-1 psql -v ON_ERROR_STOP=1 `
        -U researchos -d researchos -f /tmp/storage-tier.sql
    if ($LASTEXITCODE -ne 0) { throw "Storage attestation was rejected" }
    & ssh -i $KeyPath "$RemoteUser@$HostName" rm -f $remote
    Write-Output "storage-tier-attestation=passed stamp=$stamp components=$($manifest.components.Count)"
} finally {
    Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
}
