param([string]$ApiBaseUrl = "http://localhost:8080")

$ErrorActionPreference = "Stop"
$doi = "10.1371/journal.pone.0239283"
$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_DISCOVERER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_DISCOVERER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()
$headers = @{ Authorization = "Bearer $token" }
$suffix = [guid]::NewGuid().ToString("N")
$questionId = "q-systematic-review-$suffix"
$planId = "plan-systematic-review-$suffix"

$payload = @{
    question = @{
        question_id = $questionId
        text = "What factors drive or inhibit adoption of open research data sharing?"
    }
    discovery_contract = @{
        contract_id = "contract-systematic-review-$suffix"
        project_id = "researchos-default"
        research_question_id = $questionId
        search_plan_id = $planId
        scope = "Exact systematic review of factors influencing open research data adoption"
        source_categories = @("scholarly_index")
        inclusion_rules = @("Exact DOI match: $doi", "Systematic literature review")
        exclusion_rules = @("DOI mismatch", "Non-systematic commentary")
        languages = @("en")
        document_types = @("review", "article", "journal-article")
        evidence_types = @("method", "result", "limitation", "conclusion")
        maximum_depth = 1
        retrieval_budget = 10
        license_policy = "open_access_only"
        human_review_policy = "structured_full_text_review_required"
        stopping_conditions = @("Exact DOI acquired and extracted")
        year_from = 2020
        year_to = 2020
    }
    query_concepts = @(
        @{
            concept_id = "concept-systematic-review-$suffix"
            preferred_term = $doi
            synonyms = @()
            disciplines = @("open science", "research data management")
            attributed_by = "researchos-targeted-discovery"
            rationale = "Exact DOI isolates the systematic review under a type-compatible contract."
        }
    )
    search_plan = @{
        plan_id = $planId
        query = $doi
        providers = @("openalex")
        limit_per_provider = 10
        year_from = 2020
        year_to = 2020
    }
}

$run = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/knowledge/discovery/runs" -Method Post `
    -Headers $headers -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json -Depth 14 -Compress)
$record = @($run.records) | Where-Object {
    ($_.doi -replace "^https?://doi\.org/", "").ToLowerInvariant() -eq $doi
} | Select-Object -First 1
if (-not $record) { throw "Exact DOI was not returned by OpenAlex." }
$source = @($record.source_records) |
    Where-Object { $_.provider -eq "openalex" } |
    Select-Object -First 1
$document = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/knowledge/discovery/runs/$($run.run_id)/documents" `
    -Method Post -Headers $headers -ContentType "application/json" `
    -Body (@{
        record_id = $record.record_id
        url = "https://journals.plos.org/plosone/article/file?id=$doi&type=printable"
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
if ($screening.status -ne "eligible") {
    throw "Systematic review remained ineligible: $($screening.status)"
}
$extraction = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/knowledge/documents/$($document.document_id)/extractions" `
    -Method Post -Headers $headers -ContentType "application/json"

[pscustomobject]@{
    doi = $doi
    run_id = $run.run_id
    document_id = $document.document_id
    inspection_id = $inspection.inspection_id
    screening_status = $screening.status
    extraction_id = $extraction.extraction_id
    parser_version = $extraction.parser_version
    evidence_objects = @($extraction.objects).Count
} | ConvertTo-Json -Depth 6
