param(
    [string]$ApiBaseUrl = "http://localhost:8080",
    [string]$RunId = "discovery-7420c93731a04b1d9a2558e886751566"
)

$ErrorActionPreference = "Stop"
$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_DISCOVERER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_DISCOVERER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()
$headers = @{ Authorization = "Bearer $token" }

$targets = @(
    @{ record_id = "1071225b85f8826346b24a2f"; doi = "10.1371/journal.pone.0261719" },
    @{ record_id = "3a9914565df9427308b1f60a"; doi = "10.1371/journal.pone.0239216" },
    @{ record_id = "d45ef2f32e39261d62342bc8"; doi = "10.1371/journal.pone.0239283" },
    @{ record_id = "e4639292f6d00ac60d00bdb1"; doi = "10.1371/journal.pone.0230416" }
)

# The metadata collection is bound to the discovery run and retains the
# provider response hash required for acquisition provenance.
$metadata = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/knowledge/discovery/runs/$RunId/metadata" `
    -Method Post -Headers $headers -ContentType "application/json"

$results = foreach ($target in $targets) {
    $record = @($metadata.records) |
        Where-Object { $_.record_id -eq $target.record_id } |
        Select-Object -First 1
    if (-not $record) {
        throw "Discovery record $($target.record_id) is unavailable in run $RunId."
    }
    $source = @($record.observations) |
        Where-Object { $_.provider -eq "openalex" } |
        Select-Object -First 1
    if (-not $source) { throw "OpenAlex provenance is missing for $($target.doi)." }

    $url = "https://journals.plos.org/plosone/article/file?id=$($target.doi)&type=printable"
    $document = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/discovery/runs/$RunId/documents" `
        -Method Post -Headers $headers -ContentType "application/json" `
        -Body (@{
            record_id = $target.record_id
            url = $url
            access_status = "open"
            license = "cc-by"
            source_provider = "openalex"
            source_response_hash = $source.response_hash
        } | ConvertTo-Json -Depth 8 -Compress)
    $inspection = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/documents/$($document.document_id)/inspections" `
        -Method Post -Headers $headers -ContentType "application/json"
    $screening = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/documents/$($document.document_id)/screenings" `
        -Method Post -Headers $headers -ContentType "application/json"

    $extraction = $null
    if ($screening.status -eq "eligible") {
        $extraction = Invoke-RestMethod `
            -Uri "$ApiBaseUrl/knowledge/documents/$($document.document_id)/extractions" `
            -Method Post -Headers $headers -ContentType "application/json"
    }
    [pscustomobject]@{
        doi = $target.doi
        document_id = $document.document_id
        inspection_id = $inspection.inspection_id
        screening_status = $screening.status
        screening_reasons = $screening.reasons
        extraction_id = $extraction.extraction_id
        parser_version = $extraction.parser_version
        evidence_objects = if ($extraction) { @($extraction.objects).Count } else { 0 }
    }
}

$results | ConvertTo-Json -Depth 10
