param(
    [string]$ApiBaseUrl = "http://localhost:8080",
    [string[]]$Doi
)

$ErrorActionPreference = "Stop"

function Read-LocalSetting {
    param([string]$Name)

    $line = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=" } |
        Select-Object -First 1
    if (-not $line) {
        throw "Local setting $Name is not configured."
    }
    return ($line -split "=", 2)[1].Trim()
}

function Invoke-KnowledgeApi {
    param(
        [ValidateSet("GET", "POST")]
        [string]$Method,
        [string]$Path,
        [object]$Body
    )

    $parameters = @{
        Uri = "$ApiBaseUrl$Path"
        Method = $Method
        Headers = @{ Authorization = "Bearer $script:DiscovererToken" }
        ContentType = "application/json"
    }
    if ($null -ne $Body) {
        $parameters.Body = $Body | ConvertTo-Json -Depth 20 -Compress
    }
    return Invoke-RestMethod @parameters
}

$script:DiscovererToken = Read-LocalSetting "RESEARCHOS_DISCOVERER_TOKEN"
$targets = @(
    @{
        doi = "10.1371/journal.pone.0268993"
        query = "10.1371/journal.pone.0268993"
        url = "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0268993&type=printable"
    },
    @{
        doi = "10.1371/journal.pone.0319334"
        query = "Reproducibility and replicability in research What 452 professors think"
        url = "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0319334&type=printable"
    }
)
if ($Doi) {
    $targets = @($targets | Where-Object { $Doi -contains $_.doi })
}
if (-not $targets) {
    throw "No configured DOI matches the requested target."
}

$results = foreach ($target in $targets) {
    $suffix = [guid]::NewGuid().ToString("N")
    $questionId = "q-plos-$suffix"
    $planId = "plan-plos-$suffix"
    $contractId = "contract-plos-$suffix"
    $payload = @{
        question = @{
            question_id = $questionId
            text = "Retrieve the exact scholarly record for DOI $($target.doi)"
        }
        discovery_contract = @{
            contract_id = $contractId
            project_id = "researchos-default"
            research_question_id = $questionId
            search_plan_id = $planId
            scope = "Canonical re-extraction of an existing PLOS research article"
            source_categories = @("scholarly_index")
            inclusion_rules = @("Exact DOI match: $($target.doi)")
            exclusion_rules = @("DOI does not exactly match $($target.doi)")
            languages = @("en")
            document_types = @("article", "journal-article")
            evidence_types = @("method", "result", "limitation", "conclusion", "claim")
            maximum_depth = 1
            retrieval_budget = 10
            license_policy = "open_access_only"
            human_review_policy = "structured_human_review_required"
            stopping_conditions = @("Exact DOI acquired and extracted")
        }
        query_concepts = @(
            @{
                concept_id = "concept-doi-$suffix"
                preferred_term = $target.query
                synonyms = @()
                disciplines = @("scholarly communication")
                attributed_by = "researchos-canonical-reextraction"
                rationale = "Exact DOI anchors the legacy evidence to its authoritative source."
            }
        )
        search_plan = @{
            plan_id = $planId
            query = $target.query
            providers = @("openalex")
            limit_per_provider = 10
        }
    }

    $run = Invoke-KnowledgeApi POST "/knowledge/discovery/runs" $payload
    $record = $run.records | Where-Object {
        if (-not $_.doi) { return $false }
        $normalizedDoi = $_.doi.ToLowerInvariant() -replace "^https?://doi\.org/", ""
        return $normalizedDoi -eq $target.doi
    } | Select-Object -First 1
    if (-not $record) {
        throw "OpenAlex did not return the exact DOI $($target.doi)."
    }
    $source = $record.source_records | Where-Object { $_.provider -eq "openalex" } |
        Select-Object -First 1
    if (-not $source) {
        throw "The exact DOI has no OpenAlex provenance record."
    }

    $document = Invoke-KnowledgeApi POST "/knowledge/discovery/runs/$($run.run_id)/documents" @{
        record_id = $record.record_id
        url = $target.url
        access_status = "open"
        license = "cc-by"
        source_provider = "openalex"
        source_response_hash = $source.response_hash
    }
    $inspection = Invoke-KnowledgeApi POST "/knowledge/documents/$($document.document_id)/inspections" $null
    $screening = Invoke-KnowledgeApi POST "/knowledge/documents/$($document.document_id)/screenings" $null
    if ($screening.status -ne "eligible") {
        throw "Screening rejected $($target.doi): $($screening.status)"
    }
    $extraction = Invoke-KnowledgeApi POST "/knowledge/documents/$($document.document_id)/extractions" $null

    [pscustomobject]@{
        doi = $target.doi
        run_id = $run.run_id
        document_id = $document.document_id
        inspection_id = $inspection.inspection_id
        screening_id = $screening.decision_id
        screening_status = $screening.status
        extraction_id = $extraction.extraction_id
        evidence_objects = @($extraction.objects).Count
    }
}

$results | ConvertTo-Json -Depth 8
