param([string]$ApiBaseUrl = "http://localhost:8080")

$ErrorActionPreference = "Stop"

$tokenLine = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
    Where-Object { $_ -match "^RESEARCHOS_DISCOVERER_TOKEN=" } |
    Select-Object -First 1
if (-not $tokenLine) { throw "RESEARCHOS_DISCOVERER_TOKEN is not configured." }
$token = ($tokenLine -split "=", 2)[1].Trim()

$suffix = [guid]::NewGuid().ToString("N")
$questionId = "q-open-science-theory-$suffix"
$planId = "plan-open-science-theory-$suffix"
$payload = @{
    question = @{
        question_id = $questionId
        text = "How do academic incentives and implementation barriers influence open-science data-sharing practices?"
    }
    discovery_contract = @{
        contract_id = "contract-open-science-theory-$suffix"
        project_id = "researchos-default"
        research_question_id = $questionId
        search_plan_id = $planId
        scope = "Independent empirical studies of open-science data-sharing policy, incentives, barriers, and implementation practices"
        source_categories = @("scholarly_index")
        inclusion_rules = @(
            "Empirical or systematic research on open-science or research-data-sharing practices",
            "Reports barriers, incentives, policy effects, adoption, compliance, or implementation mechanisms",
            "Scholarly journal article published from 2018 onward"
        )
        exclusion_rules = @(
            "Editorial, news item, correction, protocol-only record, or non-scholarly commentary",
            "Open access is mentioned only as a publishing model without data-sharing or research-practice analysis",
            "No interpretable relationship between policy, incentives, barriers, and researcher or journal practice"
        )
        languages = @("en")
        document_types = @("article", "journal-article")
        evidence_types = @("method", "result", "limitation", "conclusion")
        maximum_depth = 1
        retrieval_budget = 50
        license_policy = "metadata_first_full_text_only_when_rights_verified"
        human_review_policy = "title_abstract_screening_then_structured_full_text_review"
        stopping_conditions = @(
            "Fifty provider records enumerated",
            "At least three independent eligible full-text studies identified",
            "Retrieval budget exhausted"
        )
        year_from = 2018
        year_to = 2026
    }
    query_concepts = @(
        @{
            concept_id = "concept-open-science-$suffix"
            preferred_term = "open science"
            synonyms = @("open research")
            disciplines = @("metascience", "scholarly communication")
            attributed_by = "researchos-targeted-discovery"
            rationale = "Defines the scientific-practice domain."
        },
        @{
            concept_id = "concept-data-sharing-$suffix"
            preferred_term = "research data sharing"
            synonyms = @("data sharing", "data availability")
            disciplines = @("research integrity", "data stewardship")
            attributed_by = "researchos-targeted-discovery"
            rationale = "Defines the observable practice to be explained."
        },
        @{
            concept_id = "concept-mechanisms-$suffix"
            preferred_term = "academic incentives"
            synonyms = @("implementation barriers", "researcher attitudes", "policy compliance")
            disciplines = @("science policy", "research evaluation")
            attributed_by = "researchos-targeted-discovery"
            rationale = "Defines candidate explanatory mechanisms without asserting a theory."
        }
    )
    search_plan = @{
        plan_id = $planId
        query = "open science data sharing incentives barriers"
        providers = @("openalex", "crossref")
        limit_per_provider = 25
        year_from = 2018
        year_to = 2026
    }
}

$run = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/knowledge/discovery/runs" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json" `
    -Body ($payload | ConvertTo-Json -Depth 16 -Compress)

$metadata = Invoke-RestMethod `
    -Uri "$ApiBaseUrl/knowledge/discovery/runs/$($run.run_id)/metadata" `
    -Method Post `
    -Headers @{ Authorization = "Bearer $token" } `
    -ContentType "application/json"

$records = @($run.records | ForEach-Object {
    [pscustomobject]@{
        record_id = $_.record_id
        doi = $_.doi
        title = $_.title
        year = $_.year
        document_type = $_.document_type
        providers = @($_.source_records.provider)
        source_count = @($_.source_records).Count
    }
})

[pscustomobject]@{
    run_id = $run.run_id
    contract_id = $run.discovery_contract.contract_id
    record_count = $records.Count
    enumerations = $run.enumerations
    metadata_summary = $metadata.summary
    records = $records
} | ConvertTo-Json -Depth 12
