param([string]$ApiBaseUrl = "http://localhost:8080")

$ErrorActionPreference = "Stop"
$bundleId = "theory-bundle-ced0d4b5692c35991721f3fc"

$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_REVIEWER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_REVIEWER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()

$reviews = @(
    @{
        theory_id = "theory-4377eb6da0ade9fe0687432b"
        rationale = "Rejected as a theory: this is a normative single-source conclusion about inclusive open science, not an explanatory abstraction supported across independent evidence or graphs."
    },
    @{
        theory_id = "theory-c66868af53295b52cebe5d0d"
        rationale = "Rejected as a theory: this is a descriptive quantitative conclusion from one evidence object and one study, not a general explanatory proposition."
    },
    @{
        theory_id = "theory-f373de5992cadf8269956183"
        rationale = "Rejected as a theory: this restates one source author's interpretation, contains extraction typography artifacts, and lacks independent or cross-graph theoretical support."
    }
)

$results = foreach ($review in $reviews) {
    $payload = @{
        theory_id = $review.theory_id
        decision = "rejected"
        rationale = $review.rationale
        occurred_at = [DateTimeOffset]::UtcNow.ToString("o")
    }
    $response = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/theories/$bundleId/reviews" `
        -Method Post `
        -Headers @{ Authorization = "Bearer $token" } `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 6 -Compress)
    $proposal = $response.proposals |
        Where-Object { $_.theory_id -eq $review.theory_id } |
        Select-Object -First 1
    [pscustomobject]@{
        bundle_id = $bundleId
        theory_id = $review.theory_id
        decision = $proposal.review_state
        review_count = @($response.reviews).Count
        bundle_hash = $response.content_hash
    }
}

$results | ConvertTo-Json -Depth 6
