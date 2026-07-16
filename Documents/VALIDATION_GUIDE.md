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

## Validation statuses

- `pass`: all configured method gates pass.
- `fail`: contradiction or another fail-safe gate is triggered.
- `incomplete`: evidence or risk-of-bias assessment is insufficient.
- `stale`: the evidence search is older than the declared maximum age.

A status is the output of the recorded assessment method and its version. It
must not be presented as universal confirmation or rejection of a scientific
claim.

The [end-to-end pilot](END_TO_END_PILOT.md) intentionally produced
`incomplete`: one open-access paper was traceable and reviewable, but one source
was insufficient for a stronger conclusion.

The [multi-source pilot](MULTI_SOURCE_PILOT.md) demonstrated that using two
papers alone does not guarantee replication: its study-specific claims remained
separate and correctly retained an `incomplete` result.
