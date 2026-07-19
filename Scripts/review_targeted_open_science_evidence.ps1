param([string]$ApiBaseUrl = "http://localhost:8080")

$ErrorActionPreference = "Stop"
$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_REVIEWER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_REVIEWER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()

$reviews = @(
    @("object-4d9e80853dc7a64b42e0ad8f","accepted","b10b3d273cdb549ea75b92d23e788a492e69f4e47c241ee5ea252fcddfe2757d","5c45786006ab1a9d3d9b73cf6f5bb5e1cb1864956da9641cfb611b87e723e4d2","observed_fact",0.94,"Complete and clean study-design statement describing the qualitative interview method."),
    @("object-01078a1a77afbed8e507ccb4","accepted","7eb010e82a700d90ec581248ba8214751d54e424d6339ff7ff253dacaf4b3a9c","5c45786006ab1a9d3d9b73cf6f5bb5e1cb1864956da9641cfb611b87e723e4d2","observed_fact",0.91,"Complete and relevant interview finding about domain-specific research-data needs."),
    @("object-11f892d2e7c8671e4c397a6d","rejected","55416c9c16761e899bfd473ebe7b63bb9ef2d1f5940fc64092d2b17e1e360df0","5c45786006ab1a9d3d9b73cf6f5bb5e1cb1864956da9641cfb611b87e723e4d2","unclear",0.35,"The passage contains useful interview findings but is misclassified as a dataset and merges quotations with narrative results; canonical type and boundaries require correction."),
    @("object-bf8d5677ea8a19b47181a189","accepted","2ee459af59b6dd73b77cbeec92c57805d3d0deb46efe4e7d84d7eb5cf344a4a5","3ba4bbb62855175785fcd11a44480d5ebaf850bdf588cf94e83caa0f138edb26","mixed",0.88,"Traceable Results section reporting the systematic review synthesis process and descriptive characteristics of the 32 included studies."),
    @("object-92e7cb666e534198c541c916","rejected","e16a4989af2d6a2aa810ceaaa504a4f6eb30d01bc7a598f78178e3e73acd6863","3ba4bbb62855175785fcd11a44480d5ebaf850bdf588cf94e83caa0f138edb26","unclear",0.38,"This is flattened table content with lost row and column structure; citation fidelity cannot be established without table coordinates."),
    @("object-cf4e7d4db938ae2b8e3c27e7","accepted","60c83bef0b0e7359782274f7b053a8e1eef899963cb056bbb6a1206e44af217e","3ba4bbb62855175785fcd11a44480d5ebaf850bdf588cf94e83caa0f138edb26","mixed",0.94,"Complete systematic-review conclusion identifying categories of drivers and inhibitors and explicitly limiting claims about their relative importance."),
    @("object-f8c919e6b91fbebd4493c53d","rejected","c1f72799d62fd017986aaca92937e4e984b6006ddc74acb7df292009e7ba9cfd","3ba4bbb62855175785fcd11a44480d5ebaf850bdf588cf94e83caa0f138edb26","unclear",0.03,"Reference-list material was misclassified as a dataset and is not admissible scientific evidence."),
    @("object-c3c7a0a143fca7d05996580a","accepted","e3897e5595d24cb8aff71033dad9469dcad23d835d01e3b37eea66c65d117f55","b09ee65461dd17b741528acbb350228b0cd38a1aaf03d595eb2af638284a8d0f","observed_fact",0.93,"Complete survey Results segment reporting the sample and the central finding that 96 percent had never shared qualitative data in a repository."),
    @("object-e4dbe0e1b8056e45c2fc8d68","rejected","7dfaa0d7b86d6037e2dcc488df55e03d2bea06e91d8b393bd6484f1b5922e693","b09ee65461dd17b741528acbb350228b0cd38a1aaf03d595eb2af638284a8d0f","mixed",0.42,"The valid limitations paragraph spills into resources guidance and flattened table content, so the reviewed statement does not preserve a single clean context.")
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
        -Method Post -Headers @{ Authorization = "Bearer $token" } `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 8 -Compress)
    [pscustomobject]@{
        evidence_id = $item[0]
        decision = $response.decision
        review_id = $response.review_id
    }
}

$results | ConvertTo-Json -Depth 6
