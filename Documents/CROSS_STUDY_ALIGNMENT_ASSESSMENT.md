# Cross-study Alignment Assessment

Status: completed; fail-closed, keep studies separate.

Date: 2026-07-19

## 1. Graphs evaluated

- `graph-bb59192c7b3c0706e5cbfe6d` — interview evidence about research-data
  needs and interviewed researchers.
- `graph-ea24fd3bf004e01a3986cd80` — systematic-review evidence about drivers
  and inhibitors of open-data sharing and use.
- `graph-b9e1f372aa7185404c5548f7` — survey evidence about qualitative
  researchers' sharing experience and attitudes.

## 2. Alignment judgment

The graphs share a broad open-research-data domain, but their accepted objects
do not express equivalent propositions:

- research-data need is not the same construct as willingness or attitude to
  share data;
- a systematic synthesis of drivers and inhibitors is not the same
  observation as a survey response distribution;
- differing populations, methods, outcomes, and scopes prevent a defensible
  equivalence claim; and
- none of the accepted passages explicitly cites or evaluates another graph's
  proposition.

Consequently:

- `supports`: no defensible cross-study assertion;
- `contradicts`: no defensible cross-study assertion; and
- `extends`: thematic adjacency exists, but explicit dependency is absent, so
  no assertion is permitted.

## 3. Executed theory gate

The verified theory builder evaluated all three current graphs and produced:

- bundle: `theory-bundle-5d3969d8d234f8188c5240e1`;
- graph count: 3;
- theory proposals: 0;
- competing theories: 0;
- reviews: 0; and
- alignments: 0.

The immutable snapshot is
`v1.3-2fa621f3077822af4e11a37ce272bc3d2520d5c3813bb1b6c9efee5bdcd116e2.json`.

This is a successful scientific gate, not a processing failure. ResearchOS
did not promote thematic similarity into evidential support.

## 4. Required evidence for a future theory

A later theory attempt requires at least two independent graph objects that:

1. express the same bounded proposition;
2. carry explicit reviewed `supports` edges;
3. retain distinct graph, object, quotation, and document provenance; and
4. agree on the relevant population, construct, outcome, and direction, or
   explicitly document their differences.

## 5. Targeted acquisition follow-up

ResearchOS executed a new discovery run for the bounded attitude–practice
question. The strongest initial Frontiers candidate,
`10.3389/fdata.2022.971974`, was discovered but not acquired because provider
metadata did not enumerate a typed, licensed PDF URL. The acquisition policy
was not bypassed.

An eligible independent PLOS study,
`10.1371/journal.pone.0229003`, was then acquired using its enumerated OpenAlex
provenance. The 26-page document passed inspection and screening and produced
`extraction-ecc22c7444117a19e35908dd` with four provisional evidence objects.
The human authority subsequently approved three objects and rejected one
over-broad, malformed extraction. Four hash-bound review events were recorded,
all current projections are consistent, and no new object was admitted to a
knowledge graph by the review operation.

Structured semantic re-extraction of the three accepted passages produced
`extraction-69cbb14e50a5262e8c51f692`: two population candidates, one
measurement candidate, and one variable candidate. All four were frozen as
pending until the separate human-review packet was approved. No limitation
was fabricated to complete annotation coverage.

The human authority subsequently approved all four semantic candidates. Four
immutable hash-bound review events were recorded, all four current projections
are accepted and consistent, and review created zero knowledge nodes.

A provenance-bound `measures` relation,
`semantic-relation-57150e5b538fe49cbb250e52`, was subsequently proposed from
the accepted greater-than-85-percent willingness measurement to the accepted
attitudes-and-behavior variable. It was frozen with zero reviews and zero
graph admissions pending the separate relation-review packet.

The human authority subsequently approved the relation. An authenticated
reviewer distinct from the discoverer recorded one accepted review; the
relation hash verified and graph admissions remained zero at review
completion.

The independent indexer then admitted all four accepted structured objects and
the reviewed relation. `intake-8be36a5690334f516d355c7b` produced
`graph-29f3e0070f7f4056ffb00114` with one source node, four evidence nodes, four
provenance edges, and one reviewed `measures` edge. Intake and graph integrity
verification passed; all four accepted evidence objects are indexed and the
relation has exactly one graph-admission event.

## 6. Repeated two-graph theory gate

The theory gate was repeated using only the two most relevant independent
structured graphs:

- `graph-b9e1f372aa7185404c5548f7`, the qualitative-researcher sharing
  experience and attitude graph; and
- `graph-29f3e0070f7f4056ffb00114`, the multinational scientist willingness
  and attitude graph.

The verified result was:

- bundle: `theory-bundle-5c3a0c3cb880a096a234f667`;
- graph dependencies: 2;
- theory proposals: 0;
- competing theories: 0;
- reviews: 0;
- alignments: 0; and
- snapshot:
  `v1.3-01a9344ac84ddaa3b4eb38d393afc6bb8090f523f562a814130bbcd43a028286.json`.

The zero-proposal result is correct under the current contract. Both graphs
contain accepted population, variable, and measurement nodes plus reviewed
`measures` relations. The theory builder requires eligible result,
conclusion, or limitation nodes with explicit `supports` edges from at least
two independent graphs. It does not treat a measurement relation as theory
support.

Further literature acquisition alone will not close this specific gap. The
next implementation increment must provide a provenance-safe route for
reviewed proposition support across the parent-result and derived-annotation
boundaries, without weakening extraction-bounded relation review or
fabricating support from co-occurrence.

## 7. Reviewer-governed cross-study proposition

The contract gap is now implemented as a reviewer-governed cross-study
proposition. A candidate must bind at least two accepted result, conclusion,
or limitation objects from at least two verified graphs and two distinct
source documents. It is immutable, hash-verified, revalidates current
evidence and graph lifecycle, prohibits proposer self-review, and cannot
produce a theory bundle before independent acceptance.

The first actual candidate is
`cross-study-proposition-93c9eec35dfbac882b061a1a`:

> Stated willingness or favorable attitudes toward research data sharing do
> not by themselves establish frequent repository sharing practice.

It binds one accepted PLOS result and one accepted independent-survey result.
Its state remains `proposed`. API restart recovery returned the same
identifier and content hash
`8a81dfec9013ada30f2eb8e2fbd2a666361e5a0e6c76ac7d75be6c6f5af101ed`.
No theory bundle has been created pending human review.

The canonical decision basis is
`CROSS_STUDY_PROPOSITION_REVIEW_PACKET.md`.
