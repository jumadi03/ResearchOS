# Local Canonical Evidence Extraction Acceptance Report

Date: 2026-07-19  
Environment: local ResearchOS stack and `http://localhost:3003/`  
Result: Accepted locally with a disclosed historical duplicate batch

## Scope

This acceptance covered the governed handoff from an eligible inspected source
to provisional evidence and the human-review queue. It did not accept or reject
any evidence on behalf of a reviewer.

## Scenario

- DOI: `10.3389/fdata.2022.971974`
- Provider: OpenAlex
- Acquired representation:
  `https://www.frontiersin.org/articles/10.3389/fdata.2022.971974/pdf`
- Verified document SHA-256:
  `81fd706a75ed80bda68c15b29af06a11c30d5d4e0c3b0df151b593193b389b5a`
- Screening result: `eligible`
- Reused extraction manifest:
  `fbcd39dd67f47d974d1d8b70aac6bec49053722bd0561fd9326bf46fd37dca09`
- Evidence returned: 5 provisional objects

## Defect found and corrected

Before the correction, repeating acquisition and extraction for identical PDF
content created a new source-document version and five duplicate evidence
objects. The project total changed from 320 to 325 and the reviewer queue from
4 to 9.

The backend now looks up an existing extraction by document content hash,
parser name, and parser version after validating the eligible screening
decision. When an equivalent extraction exists, it returns the canonical
manifest instead of persisting another evidence batch. Raw acquisition records
remain immutable.

The pre-fix duplicate batch remains in the local acceptance database as an
explicit test artifact; it was not silently deleted or rewritten.

## Actual acceptance result

After rebuilding the local API, the full browser flow was repeated:

1. Governed discovery returned one unique record.
2. Acquisition reproduced the verified checksum.
3. Inspection was valid and screening was eligible.
4. Extraction returned the same five-object manifest.
5. The project stayed at 325 objects.
6. The evidence-review queue stayed at 9.
7. After a full browser refresh, the project remained at 325 and the queue at
   9.

The browser labels the extracted objects as provisional, awaiting a human
reviewer, and not yet accepted as evidence. Refresh clears only transient form
state; canonical project and queue data are reloaded from the backend.

## Regression evidence

- Targeted backend tests: 65 passed.
- Full backend regression: 504 passed.
- Canonical UI behavior tests: 7 passed.
- Canonical Vinext production build: passed.

## Decision

The local canonical extraction handoff is accepted. Equivalent repeated
extraction is idempotent, evidence remains provisional, and the reviewer queue
persists across refresh. Human reviewer decisions remain a separate governed
action.
