param([string]$ApiBaseUrl = "http://localhost:8080")

$ErrorActionPreference = "Stop"

$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_INDEXER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_INDEXER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()

$intakes = @(
    @{
        doi = "10.1371/journal.pone.0268993"
        extraction_id = "extraction-4084efc2ff48067d7c5ff351"
        evidence_object_ids = @(
            "object-e266cdef1c7e3594d32461ee",
            "object-dfbd1a28479a591db77c1856",
            "object-efb03854858cfe790d5ca3c5",
            "object-82adab40cdfa329384a90cb0",
            "object-7abe569ba30e9ada77700c28",
            "object-fdfc08499833bd2e68981733"
        )
    },
    @{
        doi = "10.1371/journal.pone.0319334"
        extraction_id = "extraction-d4e007e0acf5741b4588d7d0"
        evidence_object_ids = @(
            "object-a40d694bd8fac3903b0ca6d1",
            "object-cb859461e2afe4751180d506",
            "object-6341cc22b3a3ef88a3b28a59",
            "object-018c27f4df0269ed26036512",
            "object-1ac6738c5b04c7eef2128512",
            "object-9476131e0730acbf4223ed11"
        )
    }
)

$results = foreach ($item in $intakes) {
    $payload = @{
        evidence_object_ids = $item.evidence_object_ids
        occurred_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $response = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/extractions/$($item.extraction_id)/intake" `
        -Method Post `
        -Headers @{ Authorization = "Bearer $token" } `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 8 -Compress)
    [pscustomobject]@{
        doi = $item.doi
        extraction_id = $item.extraction_id
        intake_id = $response.intake.intake_id
        graph_id = $response.graph.graph_id
        admitted = @($response.intake.admitted_evidence_object_ids).Count
        nodes = @($response.graph.nodes).Count
        edges = @($response.graph.edges).Count
        integrity_verified = $response.integrity_verified
    }
}

$results | ConvertTo-Json -Depth 6
