# Structured Semantic Re-extraction Human Review Packet

Status: human-approved and recorded in the canonical review ledger.

Date prepared: 2026-07-19

## 1. Review boundary

This packet evaluates the 50 provisional objects produced by
`researchos-semantic-annotation-parser` version `1.0.0`. Recommendations use
the SGF evidence criteria: citation fidelity, context preservation, relevance,
confidence, and epistemic classification.

An `accept` recommendation means that the quoted statement genuinely supports
the assigned canonical object type. A `reject` recommendation means that the
quote is exact but the assigned type is not defensible, the passage is
truncated, or the candidate is a misleading duplicate. The complete
recommendation packet was presented to and approved by the human authority
before any review event was written.

## 2. Recommended outcome

- Accept: 36 objects.
- Reject: 14 objects.
- Remain pending because evidence is ambiguous: 0 objects.

Accepted descriptive statements should normally be classified as
`observed_fact`. Statements that synthesize, interpret, or generalize the
source literature should normally be classified as
`source_author_interpretation`.

## 3. Recommended accept

### extraction-aef6f19024c52d04de262457

- `object-ee9a20ad63c597288eaedba9` — population; interviewees are the explicit
  participant group.
- `object-e182a82ac0ed6d22becaf7d2` — population; interviewed researchers are
  the explicit participant group.

### extraction-888adf6b1db2130f41ac8037

- `object-fcd81c224cb5224c13454717` — measurement; explicit sample size
  (`n = 32`).
- `object-aa5e79bcc22eb635be3dd228` — variable; the comprehensive factor
  overview is the construct under synthesis.
- `object-792b070b58f9aaadaabc756c` — measurement; publication-year
  distribution.
- `object-7279404998b455a35ce7fee3` — measurement; explicit publication counts.
- `object-49c6fbe003e05cf05707bb98` — population; individual researchers are
  the target population of the reviewed phenomenon.
- `object-5ad4738024ab086a0be757a2` — variable; drivers and inhibitors are the
  explicit constructs.
- `object-ca54eb5d7527bc6320361e99` — measurement; explicit study-design
  counts.
- `object-d006a600d5f7de3b2a5a855e` — measurement; explicit discipline count.
- `object-8cdd5ecff4a2d59bdb0d4bbb` — measurement; explicit count of studies
  without a stated theory.
- `object-72b904406546d16ace18378b` — measurement; explicit theory-frequency
  counts.
- `object-e8c898b0856dba7b8716c721` — variable; four driver/inhibitor construct
  groups.
- `object-b74b7f7691a748139153a39d` — variable; eleven factor categories.
- `object-5ba7c2cada3abc354aff27f8` — variable; sharing drivers.
- `object-1fe585aa8e44c57c27309a3b` — variable; sharing inhibitors.
- `object-c401fd4633c78f4b35df2ce8` — variable; data-use drivers.
- `object-d608f41b3a29f3f29a5d459a` — variable; data-use inhibitors.
- `object-3de0ea331e8daed8d60f20dc` — limitation; factor frequency does not
  establish importance and further research is required.
- `object-7f1c9b7f712ba2696dd3ecca` — variable; drivers and inhibitors remain the
  constructs discussed in the limitation statement.
- `object-4b22166cb979db541320f14f` — variable; diversity of influencing
  factors is the construct being interpreted.

### extraction-ea43bc19d859edbd58a51f8e

- `object-8aa80b2068fbb3714b6bdfe0` — measurement; demographic counts and
  percentages.
- `object-b28780f263393954330d3071` — population; participants are explicitly
  characterized.
- `object-5ccc03f71d2fdadeedc66ff7` — measurement; experience and data-type
  counts.
- `object-0019299e0100cc413aa8f7b5` — population; qualitative researchers are
  explicitly characterized.
- `object-18ded7d8fc2be29917909190` — measurement; counts across researched
  population groups.
- `object-fd35863b9b9a87661f749c41` — population; explicit populations studied
  by survey participants.
- `object-24b8e8722371a89bef8f3174` — measurement; qualitative-method counts.
- `object-61ef1b785a50e192250b8424` — population; respondents are the explicit
  actors whose methods are reported.
- `object-039a685b6a84478197bc3f23` — measurement; funding-source counts.
- `object-444db4a0e121a5466d70309b` — measurement; repository-sharing count and
  percentage.
- `object-8268145275c7c82c0d29305c` — population; researchers are the group
  whose sharing experience is measured.
- `object-31be8fc430d602ad6e132feb` — variable; experience and attitude toward
  qualitative data sharing.
- `object-654205c248e64bcefd05a52b` — measurement; explicit seven-point Likert
  measurement.
- `object-e6ac18f35606cb6707c11886` — population; qualitative researchers are
  the measured group.
- `object-f7586dc73bb887c61a793fdc` — variable; attitude toward qualitative
  data sharing.

## 4. Recommended reject

### extraction-aef6f19024c52d04de262457

- `object-5b3ffcec304d3f4b3e438259` — “only a few” is a substantive result, not a
  study limitation.

### extraction-888adf6b1db2130f41ac8037

- `object-6deadf1485ce13b7faff9fd3` — assessors are review-process actors, not the
  studied population.
- `object-4f4ee442e3d2292ed56dc594` — mention of researchers occurs inside a
  factor synthesis; the statement does not define a population object.
- `object-876cf9fc17e79d238a97aaea` — “researcher’s background” triggered a
  population match, but it names a factor category.
- `object-d23377455e1789471a71c46f` — passage is truncated at “e.” and does not
  preserve sufficient context.
- `object-3ec2b308caab8d78aeefe018` — truncated fragment naming a category, not
  a population.
- `object-7cfaec34482e9c1e9d753fa8` — researchers appear as the possessor of
  expected performance; no population is defined.
- `object-3d6c762378b618475dd01d7e` — researchers appear inside a driver
  statement; no population is defined.
- `object-b32f859c762f1e2ae1c02366` — “number” is discussed as an invalid proxy
  for importance; the defensible primary annotation is limitation, already
  represented by `object-3de0ea331e8daed8d60f20dc`.
- `object-e44c99ab624197fd19b11974` — “other researchers” are prospective
  users of the analysis, not a study population.

### extraction-ea43bc19d859edbd58a51f8e

- `object-498639ccea19e2f51a2e0062` — exclusion is a sampling-flow statement and
  the passage is truncated at “i.”; it is not yet a defensible limitation.
- `object-438e24dbbf0756aa7f73da2d` — the respondent statement is truncated and
  lacks the exclusion criteria needed to preserve context.
- `object-6ce2d76b3f9f185139fb85e7` — population statement is truncated at
  “the U.” and lacks the geographic qualifier.
- `object-4520dc6c19d5640086801440` — merely points to a demographic table and
  does not itself characterize the population.

## 5. Authority checkpoint and execution record

The human reviewer approved the complete 36-accept and 14-reject packet. The
authenticated reviewer workflow then recorded:

1. 50 immutable, statement-hash-bound and manifest-hash-bound review events;
2. 36 current accepted projections;
3. 14 current rejected projections;
4. 50 of 50 stored states consistent with the current review projection; and
5. zero knowledge nodes created from these objects at review time.

Acceptance therefore changes evidence authority only. It does not itself
create semantic relations, perform intake, build a graph, or promote a theory.
