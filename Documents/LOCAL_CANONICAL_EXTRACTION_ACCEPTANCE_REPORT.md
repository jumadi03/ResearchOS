# Local Canonical Evidence Extraction Acceptance Report

Date: 2026-07-20  
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
- Final full backend regression: 505 passed.
- Canonical UI behavior tests: 7 passed.
- Canonical Vinext production build: passed.

## Human-review completion

The reviewer completed the nine-item acceptance batch. Eight malformed,
truncated, or duplicate objects were rejected. One complete claim from page 10
was initially rejected by mistake and then corrected through a second,
append-only review event:

- evidence object: `object-a369437ab603049f6edddf86`;
- statement: demographic control variables explained 1% of outcome variance;
- original transition: `pending -> rejected`;
- corrective transition: `rejected -> accepted`;
- final canonical status: `accepted`.

The original rejection was not deleted or rewritten. Both events remain
attributed to the reviewer and retain their timestamps.

## Additional defects corrected during reviewer acceptance

- The reviewer dialog now displays the complete statement, source-document
  title, DOI, page, section, character range, statement hash, and manifest
  hash before confirmation.
- Duplicate development-mode session loads no longer race CSRF rotation.
  A stale CSRF response refreshes the session without automatically replaying
  a scientific decision.
- Advisory guidance is explicitly labelled as non-decisional and does not
  preselect or submit reviewer assessments.
- Rejected evidence is retained as an audit archive and no longer appears as
  active correction work. A completed correction leaves the active queue.

## Decision

Stage 4 is accepted locally end to end. Equivalent repeated extraction is
idempotent, provisional evidence reaches the human reviewer, reviewer
decisions are source- and hash-bound, corrections are append-only, and rejected
history remains auditable without polluting the active queue.
