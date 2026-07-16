# Theory Validation Guide

ResearchOS validation is a transparent, versioned assessment of an
evidence-linked theory bundle. It is not a probability that a theory is true
and does not replace scientific peer review.

## Who can validate

Theory validation requires an authenticated `reviewer` principal. The reviewer
identity is derived from the session or Bearer token and cannot be supplied in
the request body.

## Risk-of-bias values

`risk_of_bias_by_theory` maps every assessed theory ID to one of four values:

| Value | Use when |
| --- | --- |
| `low` | The reviewed evidence has no material identified bias concern under the chosen assessment method. |
| `some_concerns` | There are credible concerns, but they do not justify a high-risk classification. |
| `high` | Material bias concerns substantially limit interpretation. |
| `unknown` | Risk of bias has not been assessed or available information is insufficient. |

Do not use synonyms such as `unclear`, `medium`, or `moderate`. The API rejects
values outside this closed vocabulary before validation begins. When no usable
assessment is available, use `unknown`; ResearchOS then remains fail-safe and
cannot report a complete validation based on that theory.

## Example request

The following body is submitted to
`POST /knowledge/theories/{bundle_id}/validations` using reviewer credentials:

```json
{
  "assessed_at": "2026-07-16T02:42:05Z",
  "search_completed_at": "2026-07-16T02:42:05Z",
  "max_age_days": 180,
  "risk_of_bias_by_theory": {
    "theory-example": "unknown"
  }
}
```

`assessed_at` records when the reviewer performed the assessment.
`search_completed_at` records the evidence-search boundary. `max_age_days`
defines when that search becomes stale; it is not an instruction to rewrite
historical timestamps.

## Independent graph consolidation

Before validation, Theory Builder consolidates conclusions only when their
normalized words are identical. Normalization handles Unicode presentation,
capitalization, punctuation, and whitespace; it does not infer that merely
similar claims have the same scientific meaning.

Every consolidated evidence assertion retains its graph ID, evidence object ID,
confidence, and quote hash. Validation counts distinct graph IDs, not repeated
wording or multiple assertions from one graph. Related claims that need semantic
alignment must therefore remain separate until a reviewer-governed decision is
applied.

### Reviewer-governed semantic alignment

Semantic alignment is an explicit mutation of a versioned theory bundle. It is
available at `POST /knowledge/theories/{bundle_id}/alignments` and requires the
`reviewer` role. ResearchOS never invokes this operation based on similarity
scores alone.

```json
{
  "theory_ids": ["theory-source-a", "theory-source-b"],
  "statement": "Open and transparent practices improve reproducibility",
  "rationale": "The reviewed constructs, direction, and outcome scope match",
  "occurred_at": "2026-07-16T04:00:00Z"
}
```

The source theories must already be accepted and must collectively contain
evidence from at least two graphs. A successful alignment records the source
theory IDs, resulting theory ID, reviewer, rationale, statement, and timestamp
in an immutable bundle event. It preserves all evidence provenance and removes
active validation reports for the older bundle content, requiring a new
validation before publication.

Reviewers can retrieve a prioritized advisory queue from
`GET /knowledge/theories/{bundle_id}/alignment-candidates`. The current
`explainable-lexical-v2` method removes common English and Indonesian stopwords,
requires at least two shared content terms and evidence spanning at least two
graphs, and combines content-term Jaccard (85%) with adjacent content-bigram
Jaccard (15%). Pairs below 0.20 or with opposing polarity are excluded. Every
candidate exposes shared terms, phrases, score components, threshold, and a
plain-language explanation. Only accepted theories are considered.

A candidate is not evidence of semantic equivalence. It is a navigation aid;
the reviewer must still inspect source statements and evidence provenance,
including document ID, page, object ID, graph ID, confidence, and quote hash.
The reviewer then either submits an alignment with a scoped rationale or records
an immutable `keep_separate` decision at
`POST /knowledge/theories/{bundle_id}/alignment-decisions`. A decided pair is
suppressed from later candidate queues so the same review is not repeated.

The immutable reviewer ledger is available from
`GET /knowledge/theories/{bundle_id}/alignment-history`. It combines aligned
and `keep_separate` events with reviewer identity, time, rationale, source
theory identifiers, preserved evidence provenance, and the latest active
validation status. Workspace audit links can reopen a bundle and highlight one
specific decision without changing the underlying event.

### Candidate quality evaluation

Every reviewer decision originating from an advisory candidate stores the
candidate ID, method, score, production threshold, and shared terms in the
immutable alignment event. Historical decisions without these fields remain
valid and are reported separately rather than assigned reconstructed scores.

Reviewers can inspect `GET /knowledge/theories/{bundle_id}/alignment-quality`.
The response combines observed `aligned`, `keep_separate`, and pending outcomes
with score distributions and the versioned `theory-alignment-benchmark` data
set. An optional `threshold` query parameter recalculates benchmark precision
and recall only. It never changes the production threshold, candidate queue,
review events, bundle hash, or publication state. The workspace labels this
operation as a simulation and shows both production and simulated thresholds.

### Theory bundle registry

The reviewer workspace loads `GET /knowledge/theories` to list available
bundles. Each entry summarizes graph and theory counts, pending reviews,
completed alignments, advisory candidates, schema version, content hash, and
the latest validation status. Selecting an entry loads its candidate queue; a
bundle ID can still be entered directly when following an external audit link.

Theory bundle and validation snapshots live on the persistent knowledge volume.
At startup, ResearchOS verifies their hashes and restores the latest append-only
state. Valid historical theory snapshots are verified in their original shape
and migrated in memory to schema 1.2; corrupt snapshots fail closed.

## Validation statuses

- `pass`: all configured method gates pass.
- `fail`: contradiction or another fail-safe gate is triggered.
- `incomplete`: evidence or risk-of-bias assessment is insufficient.
- `stale`: the evidence search is older than the declared maximum age.

A status is the output of the recorded assessment method and its version. It
must not be presented as universal confirmation or rejection of a scientific
claim.

### Decision-triggered revalidation

Every validation report is bound to both the theory bundle ID and its exact
content hash. A reviewer decision or later review that changes bundle content
makes earlier reports historical and inactive; those reports remain available
from `GET /knowledge/theories/{bundle_id}/validation-history` but cannot be used
to publish the current bundle.

The reviewer workspace exposes `Revalidate bundle`, requires a risk-of-bias
assessment for every active theory, records literature-search completion and
maximum age, and displays every theory-level gate reason. When revalidation is
opened from the decision ledger, `triggered_by_decision_id` links the immutable
report to its initiating alignment or `keep_separate` event. Publication fails
closed if the selected report hash does not match current bundle content.

### Publication readiness and immutable release

`GET /knowledge/theories/{bundle_id}/publication-readiness` evaluates the same
server-side checklist used by final publication. It verifies input integrity,
exact validation currency, completion of theory review, at least one accepted
theory, absence of unresolved competition between accepted theories, complete
evidence provenance, and the validation policy for the requested publication
kind.

All publication kinds reject `fail` and `stale` validation. Systematic-review
support requires `pass`; literature reviews, scoping reviews, research
proposals, and evidence briefs may explicitly carry `incomplete` validation and
its limitations. Only accepted theories are rendered into the synthesis.

`POST /knowledge/theories/{bundle_id}/publication-preview` renders canonical
Markdown and verifies citations without releasing an artifact. Final publish
uses the identical readiness function and creates an immutable package.
Integrity-verified packages are restored after restart and listed at
`GET /knowledge/theories/{bundle_id}/publication-history` with their theory and
validation hashes.

The [end-to-end pilot](END_TO_END_PILOT.md) intentionally produced
`incomplete`: one open-access paper was traceable and reviewable, but one source
was insufficient for a stronger conclusion.

The [multi-source pilot](MULTI_SOURCE_PILOT.md) demonstrated that using two
papers alone does not guarantee replication: its study-specific claims remained
separate and correctly retained an `incomplete` result.
