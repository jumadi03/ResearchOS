param(
    [string]$ApiBaseUrl = "http://localhost:8080"
)

$ErrorActionPreference = "Stop"

function Read-LocalSetting {
    param([string]$Name)
    $line = Get-Content (Join-Path $PSScriptRoot "..\deploy\local-access.env") |
        Where-Object { $_ -match "^$([regex]::Escape($Name))=" } |
        Select-Object -First 1
    if (-not $line) { throw "Local setting $Name is not configured." }
    return ($line -split "=", 2)[1].Trim()
}

$reviewerToken = Read-LocalSetting "RESEARCHOS_REVIEWER_TOKEN"
$manifest0268993 = "762d8387d519e7b220ac0f5edcede37736e56cbb3932e70e1360ee0eff1347d7"
$manifest0319334 = "6f7915c6a6936827e161f4447201b44775d6b33f424d1b9d948b82a588c0cdcb"

$reviews = @(
    @{
        id = "object-417ad71cbcdb287e7e39c83c"; decision = "accepted"
        hash = "1fce5f6dca73a6778a20d62abaf7210f1eeeb7698a7266a40b42a6018cf5f1e5"
        manifest = $manifest0268993; fidelity = $true; context = $true; relevant = $true
        confidence = 0.92; epistemic = "observed_fact"
        rationale = "The Methods statement is complete, traceable to page 1, relevant to the study design, and contains no page furniture or unrelated material."
    },
    @{
        id = "object-67d5c990d82ae86aaeadbc73"; decision = "accepted"
        hash = "9c7a6a8f7d5e92d7b8db54c4de9dbe8eedc39bc3330179e3781d82f2f7ae90c8"
        manifest = $manifest0268993; fidelity = $true; context = $true; relevant = $true
        confidence = 0.91; epistemic = "mixed"
        rationale = "The Results statement is complete, quantitatively specific, traceable to page 1, and preserves the authors' interpretive framing."
    },
    @{
        id = "object-7b7225971add1eb367774b57"; decision = "rejected"
        hash = "9a375f3a57333876dbf50c5ec671df5bff83f298be9d7a245f2cc92e3ba0e1f6"
        manifest = $manifest0268993; fidelity = $true; context = $false; relevant = $true
        confidence = 0.32; epistemic = "mixed"
        rationale = "The conclusion is followed by journal headers, citation metadata, licensing, funding, and other page furniture; the extracted statement does not preserve a clean scientific context."
    },
    @{
        id = "object-3664667f4c3af920ef6bc7e9"; decision = "rejected"
        hash = "e5d2fc62ebf2510289f9a771c0577adbd0360c4233e2a03a0062988cb56fb423"
        manifest = $manifest0268993; fidelity = $true; context = $false; relevant = $true
        confidence = 0.44; epistemic = "observed_fact"
        rationale = "The method passage crosses into page headers, funding text, and competing-interest metadata, so its boundaries are not suitable for canonical evidence."
    },
    @{
        id = "object-69a2335f86fca82210cf45dc"; decision = "rejected"
        hash = "e382ac0a7e6246d008467ad0d14beded5e0070359e866e04f7889a55c4e046fe"
        manifest = $manifest0268993; fidelity = $true; context = $false; relevant = $true
        confidence = 0.56; epistemic = "observed_fact"
        rationale = "The substantive result is relevant, but the extraction includes journal and page footer material; evidence boundaries require correction before acceptance."
    },
    @{
        id = "object-3d20701c17fbcbf02bbd904f"; decision = "rejected"
        hash = "f3114a9d2639881ddf1875a8875447bbe3641865bdea1690af2c104134b72f28"
        manifest = $manifest0268993; fidelity = $true; context = $false; relevant = $true
        confidence = 0.43; epistemic = "mixed"
        rationale = "The conclusion is contaminated by supporting-information and author-contribution sections plus page furniture, so context is not preserved."
    },
    @{
        id = "object-8fa79062fd1dfd3c64cf7798"; decision = "rejected"
        hash = "706e85615e568d12b221e766207567d89cc1c50ed54576d6c907f7d0f9c74dbc"
        manifest = $manifest0268993; fidelity = $false; context = $false; relevant = $false
        confidence = 0.05; epistemic = "unclear"
        rationale = "This object is author-contribution and reference-list material misclassified as a scientific method; it is not admissible evidence."
    },
    @{
        id = "object-c839eee0ed27c5f4cd287769"; decision = "rejected"
        hash = "f56ae9fc16407ca92b61a4f6072b895aaffa1ae326fd540ce8beeb0c0766ea57"
        manifest = $manifest0319334; fidelity = $true; context = $false; relevant = $true
        confidence = 0.58; epistemic = "observed_fact"
        rationale = "The methodology is relevant but overlong, crosses multiple subsections, ends mid-context, and includes page furniture; it must be segmented before acceptance."
    },
    @{
        id = "object-372d31626ac0520eec9cdd53"; decision = "rejected"
        hash = "49a5a0190ebbd9dc446f058bd647a1bc25445126be47ccb7bb4f6dd2865970d6"
        manifest = $manifest0319334; fidelity = $true; context = $false; relevant = $true
        confidence = 0.31; epistemic = "observed_fact"
        rationale = "The result terminates mid-sentence at a page boundary and includes a page footer; the quantitative claim is incomplete."
    },
    @{
        id = "object-95685fd3e26ca85fc89a2ca6"; decision = "rejected"
        hash = "262dd21f613f359ae45dbc76042c18b95ddd16799aa8af446477a4db0555842d"
        manifest = $manifest0319334; fidelity = $false; context = $false; relevant = $false
        confidence = 0.02; epistemic = "unclear"
        rationale = "The fragment 'We find that 26.' is incomplete and cannot support an interpretable or verifiable scientific claim."
    },
    @{
        id = "object-c7313148c430883018fa9ed4"; decision = "rejected"
        hash = "13bd47ccac6bdac87ee9fc5e32c9c359dee2c90a9327cb22bb7e8ee1db54d42a"
        manifest = $manifest0319334; fidelity = $false; context = $false; relevant = $false
        confidence = 0.02; epistemic = "unclear"
        rationale = "The fragment ending with 'we find that 55.' is incomplete and lacks the quantity, comparison, and surrounding context required for review."
    },
    @{
        id = "object-3bd5b033ba4cfe7db555ce6e"; decision = "rejected"
        hash = "9acbed4402a4858b6df1360846e8082c8551e534ce4d628852d88b24351485b8"
        manifest = $manifest0319334; fidelity = $true; context = $false; relevant = $true
        confidence = 0.46; epistemic = "mixed"
        rationale = "The limitations passage spills into discussion, recommendations, a figure caption, an inconsistent DOI line, and page furniture; its evidence boundary is not preserved."
    },
    @{
        id = "object-03166870e962b9e9b0dbd054"; decision = "rejected"
        hash = "62799d3188dc32ac4d7809fcfae8135779fc2ecb732f0ac4aa4361b1312a367f"
        manifest = $manifest0319334; fidelity = $true; context = $false; relevant = $true
        confidence = 0.51; epistemic = "source_author_interpretation"
        rationale = "The conclusion is substantively relevant but includes author-contribution material, so the extracted boundaries do not preserve a clean conclusion."
    },
    @{
        id = "object-f55f26013a859feec3f6290d"; decision = "rejected"
        hash = "3b69b87a8c0d9237280cf0d5f07ce152e74109a96bc2fef7fc165208ba128f57"
        manifest = $manifest0319334; fidelity = $false; context = $false; relevant = $false
        confidence = 0.04; epistemic = "unclear"
        rationale = "This object consists of author contributions and references misclassified as methodology; it is not scientific evidence from the study method."
    }
)

$results = foreach ($review in $reviews) {
    $payload = @{
        decision = $review.decision
        rationale = $review.rationale
        occurred_at = [DateTimeOffset]::UtcNow.ToString("o")
        citation_fidelity = $review.fidelity
        context_preserved = $review.context
        relevant = $review.relevant
        confidence_assessment = $review.confidence
        epistemic_classification = $review.epistemic
        reviewed_statement_hash = $review.hash
        extraction_manifest_hash = $review.manifest
    }
    $response = Invoke-RestMethod `
        -Uri "$ApiBaseUrl/knowledge/evidence/$($review.id)/reviews" `
        -Method Post `
        -Headers @{ Authorization = "Bearer $reviewerToken" } `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 10 -Compress)
    [pscustomobject]@{
        evidence_id = $review.id
        decision = $response.decision
        review_id = $response.review_id
    }
}

$results | ConvertTo-Json -Depth 6
