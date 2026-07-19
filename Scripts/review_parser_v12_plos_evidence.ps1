param([string]$ApiBaseUrl = "http://localhost:8080")

$ErrorActionPreference = "Stop"

$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_REVIEWER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_REVIEWER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()

$manifestA = "5b4a0c77dc07c07ba57df5302b80796b80b1f3e5cf7bf5b6147ef71a77064034"
$manifestB = "0ebb5533781926c25bcef711c13ef598b86e6110b63536ca169d961cc0cf709c"
$reviews = @(
    @("object-e266cdef1c7e3594d32461ee", "accepted", "1fce5f6dca73a6778a20d62abaf7210f1eeeb7698a7266a40b42a6018cf5f1e5", $manifestA, "observed_fact", 0.94, "Complete and clean Methods passage with source coordinates and no page furniture."),
    @("object-dfbd1a28479a591db77c1856", "accepted", "9c7a6a8f7d5e92d7b8db54c4de9dbe8eedc39bc3330179e3781d82f2f7ae90c8", $manifestA, "mixed", 0.93, "Complete Results passage preserving both quantitative findings and the authors' framing."),
    @("object-efb03854858cfe790d5ca3c5", "accepted", "fbd240f786081fe4551ca37341ec1ee101f7c7beb453fff13a42a55426b732fb", $manifestA, "source_author_interpretation", 0.88, "Conclusion is now bounded before publication metadata and retains a coherent author interpretation."),
    @("object-82adab40cdfa329384a90cb0", "accepted", "ab250330549f40141584ba03aca4f09ae7c72ab19c8c145380d87dbb26e84d32", $manifestA, "observed_fact", 0.94, "Method description is complete, relevant, and cleanly bounded before page furniture."),
    @("object-7abe569ba30e9ada77700c28", "accepted", "218048a4b2d5043867b9e8e5cced3f65e12f287b92142ba8484dd2e3b1208d5b", $manifestA, "observed_fact", 0.93, "Quantitative Results passage is complete and no longer contains journal headers or footer text."),
    @("object-fdfc08499833bd2e68981733", "accepted", "ae2e0fd716c8b0b0d093abcc9e0a078a64ade649bef30799c45a4b4851aa7c18", $manifestA, "mixed", 0.92, "Conclusion is cleanly separated from supporting information and author contributions."),
    @("object-a40d694bd8fac3903b0ca6d1", "accepted", "fcc51078430c899253604eea14afc82cfef334b9b4b89602f76f2fd9662950d7", $manifestB, "observed_fact", 0.95, "Study-design overview is complete, traceable, relevant, and bounded at the Survey recruitment subsection."),
    @("object-cb859461e2afe4751180d506", "accepted", "9969e1cb9dda5c063cbf4c1d405bd23f2a9998d67063bf12298d8f7e25649dea", $manifestB, "observed_fact", 0.95, "Survey recruitment and response details form a complete, internally coherent method segment."),
    @("object-6341cc22b3a3ef88a3b28a59", "accepted", "2c3d45832ea5b4142e745caabc6db276c4ec68a8d2df6113d9ad46244faf1d59", $manifestB, "observed_fact", 0.94, "Data-collection segment is complete and ends before the page footer rather than mid-sentence."),
    @("object-ad2b491e20b3c6c54056be23", "rejected", "a5f7badabd6f767daee0901e17bb3a7a7e47b7ff02c3835f41262193ae054f83", $manifestB, "unclear", 0.18, "This is only a section-navigation sentence and contains no scientific finding suitable for evidence admission."),
    @("object-018c27f4df0269ed26036512", "accepted", "73491cb7b1146f504d6461d841324e49fe83e61b78a3f307b8cb9456f9a29eaa", $manifestB, "observed_fact", 0.91, "The bounded Results subsection contains a complete quantitative finding and excludes the truncated next-page sentence."),
    @("object-1ac6738c5b04c7eef2128512", "accepted", "edf7b11d1aff50b3462cb92ce6617fa51ba35e46554285cfdff014e4581f75b8", $manifestB, "mixed", 0.93, "Limitations are complete and cleanly bounded before Discussion and recommendations."),
    @("object-9476131e0730acbf4223ed11", "accepted", "89ac95655bbf88ad8c0dc541f4cf16795b693a1fbe96f2321c3ab3d564aae211", $manifestB, "source_author_interpretation", 0.92, "Conclusion preserves the authors' interpretation and now excludes author-contribution material.")
)

$results = foreach ($item in $reviews) {
    $accepted = $item[1] -eq "accepted"
    $payload = @{
        decision = $item[1]
        rationale = $item[6]
        occurred_at = [DateTimeOffset]::UtcNow.ToString("o")
        citation_fidelity = $accepted
        context_preserved = $accepted
        relevant = $accepted
        confidence_assessment = $item[5]
        epistemic_classification = $item[4]
        reviewed_statement_hash = $item[2]
        extraction_manifest_hash = $item[3]
    }
    $response = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/evidence/$($item[0])/reviews" `
        -Method Post `
        -Headers @{ Authorization = "Bearer $token" } `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 8 -Compress)
    [pscustomobject]@{
        evidence_id = $item[0]
        decision = $response.decision
        review_id = $response.review_id
    }
}

$results | ConvertTo-Json -Depth 5
