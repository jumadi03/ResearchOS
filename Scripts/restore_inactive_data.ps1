[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$ItemId,
    [Parameter(Mandatory)][string]$Destination
)

$ErrorActionPreference = "Stop"
$container = "researchos-archive-postgres-1"
$postgresUser = "researchos"
$destinationPath = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $destinationPath) {
    throw "Restore destination already exists; inactive archives never overwrite files"
}
$parent = Split-Path -Parent $destinationPath
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw "Restore destination parent does not exist"
}

$row = @(& docker exec $container psql -At -U $postgresUser -d postgres `
    -c "SELECT content_sha256 || '|' || encode(content,'base64') FROM local_inactive_archive_items WHERE item_id = '$ItemId'::uuid")
if ($LASTEXITCODE -ne 0 -or $row.Count -eq 0) {
    throw "Inactive archive item was not found"
}
$joined = $row -join ""
$separator = $joined.IndexOf("|")
if ($separator -ne 64) { throw "Inactive archive payload is malformed" }
$expectedHash = $joined.Substring(0, 64)
$encoded = $joined.Substring(65)
$bytes = [Convert]::FromBase64String($encoded)
[IO.File]::WriteAllBytes($destinationPath, $bytes)
$actualHash = (Get-FileHash -LiteralPath $destinationPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $expectedHash) {
    Remove-Item -LiteralPath $destinationPath -Force
    throw "Restored inactive archive checksum mismatch"
}

$restoreId = [guid]::NewGuid().ToString()
$destinationSql = $destinationPath.Replace("'", "''")
$sql = @"
INSERT INTO local_inactive_archive_restores(
    restore_id,item_id,destination,restored_sha256,verification
) VALUES (
    '$restoreId','$ItemId'::uuid,'$destinationSql',
    '$actualHash','{"checksum_verified":true,"archive_remains_inactive":true}'::jsonb
);
"@
$sql | & docker exec -i $container psql -v ON_ERROR_STOP=1 `
    -U $postgresUser -d postgres
if ($LASTEXITCODE -ne 0) {
    Remove-Item -LiteralPath $destinationPath -Force
    throw "Could not record inactive archive restoration"
}
Write-Output "inactive-restore=passed item_id=$ItemId destination=$destinationPath sha256=$actualHash"
