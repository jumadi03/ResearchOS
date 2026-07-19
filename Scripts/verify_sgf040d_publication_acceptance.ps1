param([string]$BaseUrl = "http://127.0.0.1:8080")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$ready = Invoke-RestMethod "$BaseUrl/ready"
if ($ready.status -ne "ready" -or -not $ready.checks.schema_version) {
    throw "ResearchOS is not ready on the expected schema"
}

$before = docker exec researchos-postgres-1 psql -U researchos -d researchos -Atc `
    "SELECT count(*) FROM publication_relationships;"
$verifier = Get-Content -Raw `
    (Join-Path $root "deploy/verify/canonical_publications.py")
$result = $verifier | docker exec -i researchos-api-1 python -
if ($LASTEXITCODE -ne 0 -or $result -notmatch "healthcheck: passed") {
    throw "Canonical publication relationship verifier failed"
}
$after = docker exec researchos-postgres-1 psql -U researchos -d researchos -Atc `
    "SELECT count(*) FROM publication_relationships;"

if ([int]$after -ne ([int]$before + 2)) {
    throw "Acceptance did not append exactly two publication relationships"
}

$violations = docker exec researchos-postgres-1 psql -U researchos -d researchos -Atc @"
SELECT count(*)
FROM publication_relationships p
LEFT JOIN provenance_events v ON v.provenance_id=p.provenance_id
WHERE v.provenance_id IS NULL
   OR v.event_type <> 'publication_relationship'
   OR length(p.content_hash) <> 64;
"@
if ([int]$violations -ne 0) {
    throw "Publication relationship integrity invariant failed"
}

[pscustomobject]@{
    status = "passed"
    schema_version = 39
    relationships_appended = 2
    relationship_count = [int]$after
    integrity_violations = [int]$violations
}
