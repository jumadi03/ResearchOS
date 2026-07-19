param([string]$ApiBaseUrl = "http://localhost:8080")

$ErrorActionPreference = "Stop"
$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_INDEXER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_INDEXER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()

$items = @(
    @{
        doi = "10.1371/journal.pone.0239216"
        extraction_id = "extraction-7e80eb1c28ce3ea22d4a173b"
        evidence_ids = @(
            "object-4d9e80853dc7a64b42e0ad8f",
            "object-01078a1a77afbed8e507ccb4"
        )
    },
    @{
        doi = "10.1371/journal.pone.0239283"
        extraction_id = "extraction-835383e16cda31c453098cf3"
        evidence_ids = @(
            "object-bf8d5677ea8a19b47181a189",
            "object-cf4e7d4db938ae2b8e3c27e7"
        )
    },
    @{
        doi = "10.1371/journal.pone.0261719"
        extraction_id = "extraction-3bffb1b0c21a6ce4df7d9773"
        evidence_ids = @("object-c3c7a0a143fca7d05996580a")
    }
)

$results = foreach ($item in $items) {
    $payload = @{
        evidence_object_ids = $item.evidence_ids
        occurred_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $response = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/extractions/$($item.extraction_id)/intake" `
        -Method Post -Headers @{ Authorization = "Bearer $token" } `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 8 -Compress)
    [pscustomobject]@{
        doi = $item.doi
        intake_id = $response.intake.intake_id
        graph_id = $response.graph.graph_id
        admitted = @($response.intake.admitted_evidence_object_ids).Count
        nodes = @($response.graph.nodes).Count
        edges = @($response.graph.edges).Count
        integrity_verified = $response.integrity_verified
    }
}

$results | ConvertTo-Json -Depth 6
