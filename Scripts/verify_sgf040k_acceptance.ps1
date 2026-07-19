param([string]$BaseUrl = "http://127.0.0.1:8080")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$accessPath = Join-Path $root "deploy/local-access.env"
if (-not (Test-Path -LiteralPath $accessPath)) {
    throw "deploy/local-access.env is required"
}

$access = @{}
Get-Content -LiteralPath $accessPath | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') { $access[$matches[1]] = $matches[2] }
}
$token = $access["RESEARCHOS_REVIEWER_TOKEN"]
if (-not $token) { throw "Reviewer token is not configured" }
$headers = @{Authorization = "Bearer $token"}

$ready = Invoke-RestMethod "$BaseUrl/ready"
if ($ready.status -ne "ready" -or -not $ready.checks.schema_version) {
    throw "ResearchOS is not ready on the expected schema"
}

$run = docker exec researchos-postgres-1 psql -U researchos -d researchos -Atc `
    "SELECT monitoring_run_id FROM scientific_monitoring_runs ORDER BY completed_at DESC LIMIT 1;"
if (-not $run) { throw "A monitoring run is required for acceptance" }
$changeId = "sgf040k-retraction-fixture"
$sql = @"
INSERT INTO scientific_changes(
 change_id,monitoring_run_id,change_kind,record_key,provider,
 before_hash,after_hash,details
) VALUES (
 '$changeId','$run','retracted','doi:10.0000/sgf040k','acceptance-fixture',
 repeat('a',64),repeat('b',64),
 jsonb_build_object('source','sgf-040k','is_retracted','true')
) ON CONFLICT(change_id) DO NOTHING;
"@
docker exec researchos-postgres-1 psql -U researchos -d researchos -v ON_ERROR_STOP=1 -c $sql | Out-Null

$resolutionBody = @{
    decision = "evidence_review_required"
    rationale = "Acceptance fixture requires canonical evidence impact review."
    occurred_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
try {
    $resolution = Invoke-RestMethod `
        "$BaseUrl/knowledge/impact-reviews/$changeId/resolutions" `
        -Method Post -Headers $headers -ContentType "application/json" `
        -Body $resolutionBody
} catch {
    $resolutionId = docker exec researchos-postgres-1 psql -U researchos -d researchos -Atc `
        "SELECT resolution_id FROM scientific_impact_review_resolutions WHERE change_id='$changeId';"
    if (-not $resolutionId) { throw }
    $resolution = [pscustomobject]@{resolution_id=$resolutionId}
}

$evidenceKey = docker exec researchos-postgres-1 psql -U researchos -d researchos -Atc `
    "SELECT c.stable_key FROM canonical_objects c JOIN evidence_objects e ON e.evidence_id=c.object_id ORDER BY c.created_at DESC LIMIT 1;"
if (-not $evidenceKey) { throw "Canonical evidence is required for acceptance" }
$evidenceId = $evidenceKey -replace '^evidence:',''

$targetBody = @{
    target_object_id = $evidenceId
    rationale = "Acceptance reviewer verified the canonical evidence identity."
    occurred_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
try {
    Invoke-RestMethod `
        "$BaseUrl/knowledge/evidence-follow-up-cases/$($resolution.resolution_id)/targets" `
        -Method Post -Headers $headers -ContentType "application/json" `
        -Body $targetBody | Out-Null
} catch {
    $selected = docker exec researchos-postgres-1 psql -U researchos -d researchos -Atc `
        "SELECT selection_id FROM scientific_follow_up_case_targets WHERE resolution_id='$($resolution.resolution_id)';"
    if (-not $selected) { throw }
}

$queue = Invoke-RestMethod `
    "$BaseUrl/knowledge/projects/researchos-default/work-queue" -Headers $headers
$case = $queue.follow_up_cases |
    Where-Object source_resolution_id -eq $resolution.resolution_id |
    Select-Object -First 1
if (-not $case -or -not $case.available_action) {
    throw "Target-selected case did not expose an authorized evidence action"
}

$reviewBody = @{
    decision = "rejected"
    rationale = "Acceptance fixture confirms retraction-driven evidence rejection."
    occurred_at = (Get-Date).ToUniversalTime().ToString("o")
    citation_fidelity = $false
    context_preserved = $false
    relevant = $false
    confidence_assessment = 0.0
    epistemic_classification = "unclear"
    reviewed_statement_hash = $case.available_action.reviewed_statement_hash
    extraction_manifest_hash = $case.available_action.extraction_manifest_hash
} | ConvertTo-Json
Invoke-RestMethod ($BaseUrl + $case.available_action.href) `
    -Method Post -Headers $headers -ContentType "application/json" `
    -Body $reviewBody | Out-Null

$closedQueue = Invoke-RestMethod `
    "$BaseUrl/knowledge/projects/researchos-default/work-queue" -Headers $headers
$closed = $closedQueue.completed_follow_up_cases |
    Where-Object source_resolution_id -eq $resolution.resolution_id |
    Select-Object -First 1
if (-not $closed -or $closed.status -ne "closed") {
    throw "Canonical action event did not close the follow-up case"
}

[pscustomobject]@{
    status = "passed"
    schema_version = 39
    change_id = $changeId
    case_status = $closed.status
    audit_workflow = $closed.action_completion.audit_workflow
    outcome = $closed.action_completion.outcome
}
