# SGF-040 — Research Object Lifecycle Standard

## Status

- Identifier: SGF-040
- Version: 1.0
- Document status: project-owner-directed operational standard
- Formal ratification status: not defined by current repository governance
- Classification: scientific lifecycle standard
- Owner: ResearchOS project
- Recorded: 2026-07-19
- Scope: creation, review, admission, release, correction, invalidation,
  supersession, deprecation, and archival of scientific objects
- Depends on: SGF-000, SGF-020, and SGF-030
- Constrains: storage, APIs, workers, workspace actions, graph, validation,
  publication, monitoring, and future SGF standards

This standard defines lifecycle semantics and transition safety. It preserves
existing runtime state vocabularies through explicit profiles rather than
forcing every object into one universal state machine.

## 1. Purpose

SGF-040 ensures that every ResearchOS object has:

- a known current state;
- an immutable history of state-changing events;
- an authorized and reproducible transition;
- explicit treatment of stale, corrected, superseded, invalidated, deprecated,
  and archived objects; and
- downstream gates that react safely when upstream state changes.

## 2. Lifecycle invariants

1. Lifecycle state and epistemic status are different dimensions.
2. Object identity remains stable across ordinary state changes.
3. Content-changing revisions create a new version and content hash.
4. Every material transition records actor, rationale, prior state, resulting
   state, occurrence time, provenance, and applicable policy.
5. Missing or stale transition context fails closed.
6. Historical events are append-only.
7. Rejection, invalidation, deprecation, and archival are not deletion.
8. Publication representations are immutable; corrections create new editions
   or linked correction artifacts.
9. AI and service actors may create provisional objects but may not satisfy a
   human decision gate.
10. Downstream objects must become stale or blocked when a required upstream
    object loses admissibility.

## 3. Common lifecycle language

The following terms may be used across profiles:

| Term | Canonical meaning |
|---|---|
| `planned` | Intent exists; governed content is not yet created |
| `draft` | Content exists and may change; not admitted for release |
| `provisional` / `pending` | Awaiting required human review |
| `review` | Under active governed assessment |
| `accepted` | Admitted by an applicable human decision |
| `rejected` | Reviewed and not admitted |
| `validated` | Applicable deterministic and review checks passed |
| `ratified` | Required authority approved the artifact for release preparation |
| `published` | Immutable released representation exists |
| `stale` | Prior result remains historical but its freshness or dependency is no longer current |
| `superseded` | A newer object or decision replaces current use |
| `invalidated` | Integrity, authority, provenance, or policy failure blocks use |
| `deprecated` | Still identifiable but discouraged or withdrawn from current use |
| `archived` | Retained for history; no ordinary active transitions |

Aliases such as `pending` and `provisional` may map to the same conceptual
phase, but their stored values must not be rewritten without a migration.

## 4. Transition event contract

Every governed transition event must contain:

- event ID;
- object ID and object type;
- object version and content hash;
- from-state and to-state;
- authenticated actor or accountable service actor;
- rationale or deterministic reason code;
- occurred-at timestamp;
- applicable decision, evidence, method, and policy references;
- provenance ID;
- event hash; and
- correction, appeal, or supersession linkage where applicable.

Idempotent replay is permitted only when the complete canonical event identity
and hash match.

## 5. Profile A — Discovery and representation

### 5.1 Discovery run

```text
planned -> running -> complete
                   -> failed
```

Provider observations and raw pages are immutable snapshots. Re-running a
query creates a new run; it does not rewrite an earlier run.

### 5.2 Acquisition

```text
candidate -> acquired
          -> metadata_only
          -> failed
```

`metadata_only` is a valid terminal acquisition result when access or license
does not permit content retrieval. It must not be treated as acquired content.

### 5.3 Source representation

Representations are content-addressed and immutable. A changed byte sequence is
a new representation/version, not an in-place update.

## 6. Profile B — Screening

```text
evaluated -> eligible
          -> ineligible
          -> human_review_required
```

Screening is a determination bound to a document content hash and inspection
manifest. A new representation or changed inspection context makes the prior
screening decision stale for extraction.

`human_review_required` must block extraction until a future explicit human
screening-resolution contract is satisfied. Current code computes this state
but does not provide a complete general-purpose human resolution lifecycle.

## 7. Profile C — Evidence

Stored compatibility mapping:

```text
Extraction: provisional
PostgreSQL projection: pending
```

Canonical transitions:

```text
provisional/pending -> accepted
                    -> rejected

accepted -> accepted   (new review event confirming current state)
accepted -> rejected   (new adverse review or correction)
rejected -> accepted   (new review with complete current evidence)
rejected -> rejected   (new confirming review)
```

Rules:

- acceptance requires all structured review criteria to pass;
- every decision is append-only and bound to statement and extraction hashes;
- the latest admissible decision may drive the current projection;
- prior decisions remain historical;
- accepted evidence may enter canonical graph admission;
- rejected or stale evidence must be excluded from new canonical graph builds;
- downstream graphs, theories, validations, and publications referencing newly
  rejected or invalidated evidence must be marked for impact review.

For consequential profiles, a single-reviewer acceptance is insufficient as
defined in SGF-020.

## 8. Profile D — Knowledge graph

```text
constructed -> verified -> admitted
                         -> rejected
```

Current implementation combines verification and admission when building a
content-addressed graph from accepted evidence. The conceptual stages remain
separate:

- `constructed`: graph structure exists;
- `verified`: content hash and internal integrity pass;
- `admitted`: every evidence node and edge passes the acceptance gate;
- `rejected`: graph cannot enter canonical use.

Graphs are immutable snapshots. Evidence changes produce a new graph and mark
dependent theories for reassessment.

## 9. Profile E — Theory

```text
proposed -> accepted
         -> rejected
```

Theory bundle snapshots are immutable and retain review events. Alignment
creates a new explicit event or resulting theory; it does not silently merge
identities.

An accepted theory becomes stale when:

- required evidence is rejected, invalidated, corrected, or superseded;
- a material contradiction is admitted;
- its validation report becomes stale;
- the theory content changes; or
- its governing method or scope changes materially.

Stale theory is not automatically rejected, but cannot satisfy a release gate
requiring current acceptance and validation.

## 10. Profile F — Validation

Validation statuses are assessment outcomes:

```text
incomplete
pass
fail
stale
```

They are not a forward-only object lifecycle. A new assessment creates a new
immutable validation report. The latest applicable report may be used as the
current projection.

Rules:

- changed theory content requires a new report;
- expired search context yields `stale`;
- contradiction or risk-of-bias inputs must remain inspectable;
- `pass` does not convert theory into fact; and
- systematic-review support requires `pass` under the current publication
  engine.

## 11. Profile G — Research artifact and publication

The existing canonical forward-only lifecycle is:

```text
planned -> draft -> review -> validated -> ratified
        -> published -> deprecated -> archived
```

Only the next edge is permitted. Every transition requires authenticated actor
and rationale.

Release rules:

- `published` requires an immutable representation and manifest;
- released content is never overwritten;
- a correction creates a linked correction object or new edition;
- supersession identifies the replacement artifact;
- deprecation does not remove access to historical provenance;
- archive is terminal for ordinary workflow.

Historical product permissions exposed a shortened path for some artifacts:
`draft -> validated -> ratified -> published`. SGF-040A reconciled that
projection with the canonical repository path by introducing one shared
transition contract. Product actions and work queues must now use
`draft -> review -> validated`; direct `draft -> validated` is prohibited.

## 12. Profile H — Monitoring

Source watch lifecycle:

```text
active <-> paused
active/paused -> expired
```

Current explicit transition API supports `active <-> paused`; expiry is an
operational terminal outcome. Acknowledging a detected scientific change
records awareness and does not accept, reject, or resolve its scientific
effect.

## 13. Correction, retraction, invalidation, and supersession

### 13.1 Correction

Creates a new event and, when content changes, a new object version or
representation. It must state what was wrong and what replaced it.

### 13.2 Retraction

A domain-specific withdrawal of a published or admitted object. Until a
dedicated `retracted` state is implemented, retraction must be represented by
an immutable retraction event plus `deprecated` or `invalidated` current-use
projection. UI must display the retraction explicitly.

### 13.3 Invalidation

Blocks use because a required integrity, authority, provenance, ethics, or
policy condition failed. It propagates a review requirement downstream.

### 13.4 Supersession

Preserves both identities and links the replaced object to its successor.
Supersession must not masquerade as factual correction.

## 14. Dependency propagation

When an upstream dependency changes:

| Upstream event | Required downstream response |
|---|---|
| Representation changes | Screening and extraction must be rerun |
| Screening invalidated | Extraction and evidence based on it become inadmissible |
| Evidence rejected/invalidated | Graph admission blocked; dependent graph snapshot superseded |
| Graph superseded | Theory requires impact review |
| Theory content changes | Validation becomes inapplicable |
| Validation stale/fail | Publication release gate reevaluated |
| Citation unresolved | Publication blocked |
| Published source retracted | Related evidence, theory, and publication enter impact review |

Propagation creates events and work items; it must not silently rewrite
historical objects.

## 15. Concurrency and stale-state safety

Transitions must:

- lock or compare the current version/state before commit;
- bind review to the exact content hash;
- reject unexpected prior state;
- be atomic with provenance creation;
- support idempotent replay by event identity;
- reject direct mutation that lacks a transition event; and
- preserve interrupted-operation recovery semantics.

## 16. UI requirements

The workspace must display:

- object type, current state, version, and provenance;
- available actions from backend authorization;
- why an action is blocked;
- stale and impacted dependencies;
- review and transition history;
- distinctions between rejected, invalidated, deprecated, retracted, and
  archived; and
- whether a displayed value is a lifecycle state, review state, or validation
  outcome.

## 17. Implementation traceability

### 17.1 Existing enforcement

- immutable discovery and provider snapshots;
- acquisition outcomes and content-addressed representations;
- integrity-bound screening decisions;
- provisional extraction and append-only evidence review;
- accepted-evidence graph admission;
- immutable theory bundles and review events;
- immutable validation reports;
- forward-only artifact lifecycle repository;
- immutable publication representations;
- active/paused source-watch transitions;
- provenance and lifecycle ledgers.

### 17.2 Required extensions and reconciliations

- human resolution for `human_review_required` screening;
- explicit graph lifecycle projection;
- stale and impact propagation across evidence, graph, theory, validation, and
  publication;
- first-class correction, invalidation, supersession, appeal, and retraction
  records;
- consequential-profile review quorum;
- safe current-state projections for theory and validation history;
- lifecycle compliance tests shared by API, repository, and UI.

### 17.3 SGF-040A implementation record

SGF-040A implements canonical artifact lifecycle alignment through:

- `app/knowledge/repositories/artifacts.py` as the shared transition contract;
- `app/knowledge/repositories/postgres.py` as repository state ownership;
- `app/knowledge/repositories/postgres_artifacts.py` as the transactional
  transition guard;
- `app/knowledge/repository_service.py` as the role-aware action projection;
- `app/knowledge/repositories/postgres_read_model.py` as the work-queue
  projection; and
- `app/knowledge/tests/test_sgf_artifact_lifecycle.py` as focused compliance
  coverage.

The focused compliance and knowledge API regression suite verified all legal
edges, skipped/reverse/repeated/terminal rejection, archived terminal
behavior, and reviewer-only action projection. This record demonstrates the
bounded SGF-040A increment only; it does not claim completion of the remaining
extensions in Section 17.2.

### 17.4 SGF-040B implementation record

SGF-040B implements the first operational stale-dependency projection through:

- the append-only evidence review ledger as the sole upstream authority;
- `TheoryDependencyImpact` as an explicit current-state projection over every
  evidence object referenced by a theory bundle;
- live canonical-ledger checks before theory revalidation and publication;
- automatic deactivation of validation reports when an upstream evidence
  dependency is no longer accepted;
- a `current_dependencies` publication-readiness gate, including impacted
  evidence identifiers and states; and
- `GET /knowledge/theories/{bundle_id}/dependency-impact` for reviewer and
  publisher visibility.

This increment deliberately derives impact from the existing evidence ledger
instead of creating a second mutable impact ledger. Historical theory bundles
and validation reports remain immutable; only their current usability
projection changes. SGF-040B covers evidence-to-theory, validation, and
publication propagation. Graph lifecycle projection, corrected publication
editions, appeals, retractions, and broader object-family propagation remain
required extensions under Section 17.2.

### 17.5 SGF-040C implementation record

SGF-040C implements explicit graph lifecycle projection without mutating
immutable graph snapshots:

- each active graph is projected as `current` when every referenced evidence
  object remains accepted in the canonical evidence ledger;
- a graph is projected as `superseded` when any referenced evidence is
  rejected or missing;
- theory dependency impact now reports graph identifiers, graph states, and
  the exact impacted graphs in addition to evidence-level impact;
- graph supersession therefore deactivates dependent validation reports and
  blocks validation or publication through the existing SGF-040B gates; and
- `GET /knowledge/graphs/{graph_id}/lifecycle` exposes the projection to
  reviewers and publishers.

The graph content hash remains unchanged and historical snapshots are never
rewritten. A replacement graph must be produced from newly admitted evidence.
Corrected publication editions are intentionally not included in SGF-040C:
the current representation store supports an edition label and immutable
versions, but it lacks a canonical `corrects`, `supersedes`, or `retracts`
relationship between publication artifacts. Adding editions without that
relationship would create ambiguous scientific history. That relationship
contract is the next required bounded increment.

### 17.6 SGF-040D implementation record

SGF-040D implements immutable publication relationships and current-use
projection:

- `corrects` links a released replacement package to the earlier package whose
  scientific content it corrects;
- `supersedes` links a released replacement package to an earlier package
  replaced for current use without claiming factual error;
- `retracts` records withdrawal of the identified publication and does not
  accept a target package;
- every relationship records publisher identity, rationale, occurrence time,
  provenance, and a content hash;
- publication packages and representations remain immutable;
- current-use projection distinguishes `current`, `corrected`, `superseded`,
  and `retracted`, including the replacement publication identifier; and
- publisher-only mutation and reviewer/publisher read endpoints expose the
  relationship ledger and lifecycle projection.

Canonical persistence is introduced by migration
`033_publication_relationships.sql`, including typed database constraints and
an immutable-ledger trigger. The API endpoints are:

- `POST /knowledge/publications/{publication_id}/relationships`; and
- `GET /knowledge/publications/{publication_id}/lifecycle`.

SGF-040D does not rewrite or delete a released publication. A correction is a
new independently validated and published package followed by an explicit
relationship event.

### 17.7 SGF-040E implementation record

SGF-040E connects continuous-monitoring retraction signals to a human impact
review queue without granting monitoring automation scientific decision
authority:

- every unresolved `retracted` scientific change is projected idempotently as
  an `impact-review:{change_id}` work item;
- the task retains source watch, monitoring run, provider, record key,
  detection time, and raw change details;
- only a reviewer may resolve the task;
- bounded routing decisions are `investigate`, `no_action`,
  `evidence_review_required`, and `publication_review_required`;
- resolution does not itself reject evidence, invalidate a graph, or retract a
  publication; those remain separate human-authorized workflows; and
- each resolution is immutable, provenance-bearing, and unique per scientific
  change.

Canonical persistence is introduced by migration
`034_scientific_impact_review.sql`. Pending tasks appear in the project work
queue under `impact_reviews`, and reviewers resolve them through:

`POST /knowledge/impact-reviews/{change_id}/resolutions`.

This preserves the boundary between automated detection, human impact triage,
and consequential lifecycle decisions.

### 17.8 SGF-040F implementation record

SGF-040F projects explicit follow-up cases from immutable impact-review
resolutions:

- `evidence_review_required` creates
  `follow-up:{resolution_id}` with case type `evidence_review` and reviewer
  authority;
- `publication_review_required` creates
  `follow-up:{resolution_id}` with case type `publication_review` and publisher
  authority;
- `investigate` and `no_action` do not create consequential follow-up cases;
- case identity and content are derived from the canonical resolution ledger,
  so replay cannot create duplicate scientific work;
- cases appear in the project work queue with source change, monitoring
  provenance, rationale, responsible role, and authorization projection; and
- every case declares `decision_automation: false`.

The case remains blocked until an authorized human selects the exact canonical
evidence object or publication package affected. SGF-040F therefore routes
work but does not infer object identity from provider metadata and does not
execute rejection, invalidation, correction, supersession, or retraction.
Because the case is a deterministic projection of migration-034's immutable
resolution ledger, no additional mutable case table or schema migration is
introduced.

### 17.9 SGF-040G implementation record

SGF-040G implements immutable, human-attributed linkage from a follow-up case
to the exact canonical object selected for further review:

- evidence follow-up cases accept only canonical evidence objects and require
  reviewer authority;
- publication follow-up cases accept only canonical publication-package
  artifacts and require publisher authority;
- repository validation confirms that target kind matches the originating
  impact-review decision;
- each resolution may select only one target, preventing silent retargeting;
- selection records selector identity, rationale, occurrence time, canonical
  object identity, provenance, and an immutable event; and
- work-queue cases move from `open` to `target_selected` while preserving the
  original impact resolution.

Migration `035_scientific_follow_up_case_targets.sql` provides the canonical
immutable linkage ledger. Target selection endpoints are:

- `POST /knowledge/evidence-follow-up-cases/{resolution_id}/targets`; and
- `POST /knowledge/publication-follow-up-cases/{resolution_id}/targets`.

Selection does not execute evidence rejection or publication retraction. It
only establishes the exact object against which the separately authorized
lifecycle workflow may proceed.

### 17.10 SGF-040H implementation record

SGF-040H opens consequential actions only after a follow-up case has an
immutable canonical target selection:

- an evidence case exposes the existing evidence-review endpoint only to a
  reviewer and uses the evidence stable identity rather than its database UUID;
- a publication case exposes the existing publication-relationship endpoint
  only to a publisher and predeclares relation type `retracts`;
- no action is exposed while a case is `open`, when stable identity is
  unavailable, or when the current principal lacks the required role;
- every exposed action declares `requires_confirmation: true`; and
- actions reuse the existing `evidence_review_event` or
  `publication_relationship` audit workflow rather than introducing a bypass.

SGF-040H is an action projection, not an automatic executor. The human must
still supply the complete evidence assessment or publication-retraction
rationale to the existing endpoint, whose own authorization, validation,
idempotency, and provenance rules remain authoritative. No schema migration is
required because schema 35 already stores the immutable case-to-target
linkage.

### 17.11 SGF-040I implementation record

SGF-040I closes the operational loop through a derived, fail-closed case
projection:

- an evidence case completes only when an evidence review event references the
  exact selected evidence object and occurs after target selection;
- a publication case completes only when a `retracts` publication relationship
  uses the exact selected publication artifact as its source and occurs after
  target selection;
- unrelated, earlier, differently targeted, or non-retraction events cannot
  close the case;
- completed cases are removed from active `follow_up_cases` and retained under
  `completed_follow_up_cases`; and
- the read model exposes the sequence `impact_resolved`, `target_selected`,
  `action_completed`, and `case_closed` with canonical event identifiers.

Closure is a deterministic projection of existing immutable ledgers, not an
independent mutable status or manual close button. No schema migration is
required: schema 35 already contains every identity needed to prove the
correlation.

### 17.12 Canonical workspace operational projection

The canonical backend workspace now renders the SGF-040 operational flow as
separate, role-aware views:

- retraction impact-review tasks and bounded triage decisions;
- active follow-up cases with blocked reasons;
- immutable canonical-target selection with explicit confirmation;
- consequential-action availability from the backend projection; and
- completed-case history with the full closure timeline.

The workspace does not infer permissions or lifecycle transitions locally.
Counts, authorization, blocked state, target linkage, available action, and
closure history are rendered from the canonical work-queue response. This is
the operational UI baseline for the later staged migration to `site/`.

### 17.13 SGF-040J consequential-action forms

The canonical workspace provides complete, confirmed forms for both
consequential follow-up paths:

- evidence review captures the decision, citation fidelity, context
  preservation, relevance, confidence assessment, epistemic classification,
  statement hash, extraction-manifest hash, rationale, and confirmation;
- publication retraction fixes relation type to `retracts`, preserves the
  immutable package, and requires publisher rationale and confirmation; and
- successful submission refreshes the queue so canonical closure projection
  moves the case into completed history.

Assessment hashes and stable identities come from the backend projection. The
browser does not reconstruct or guess scientific provenance.

### 17.14 Data-backed current-review and publication acceptance

Schema 38 closes the database findings from the operational SGF-040 audit:

- `evidence_current_review_projection` derives current review state from the
  latest structured, statement-bound, and extraction-manifest-bound admissible
  decision;
- legacy acceptance without the required structured context fails closed to
  `pending`, while an existing rejection remains rejected;
- the projection covers every `evidence_objects` row and the canonical storage
  healthcheck rejects either missing coverage or status drift;
- evidence admission and workspace reads consume this projection instead of
  treating the latest raw historical event as automatically admissible; and
- the publication verifier appends data-backed `corrects` and `retracts`
  relationships, verifies provenance and content hashes, replays
  idempotently, and proves that the immutable-ledger trigger rejects deletion.

Migrations `036_evidence_current_review_projection.sql`,
`037_legacy_evidence_projection_coverage.sql`, and
`038_legacy_rejection_fail_closed.sql` preserve the actual migration history
used to discover and close the two legacy-data compatibility cases. The
acceptance runner is `Scripts/verify_sgf040d_publication_acceptance.ps1`.

### 17.15 Raw-capture replay and canonical re-extraction

Schema 39 closes the operational provenance gap found while replaying legacy
PLOS evidence:

- `representation_capture_events` records each immutable raw-capture
  observation even when newly acquired bytes are content-identical to an
  existing representation;
- a fresh capture creates a new document version when the matching legacy
  document cannot prove its capture manifest, preserving the legacy record
  without treating it as verified;
- source inspection accepts only a capture hash stored on the representation
  or proven by the immutable capture-event ledger;
- screening resolves the document against the matching discovery run,
  `query_family_id`, and `source_definition_id`, rather than selecting an
  unrelated older run that happens to contain the same scholarly record; and
- `Scripts/reextract_pending_plos.ps1` provides a fail-closed operational
  replay from discovery through extraction.

The 2026-07-19 operational replay acquired and screened two exact PLOS DOI
records as eligible and persisted two extraction manifests with seven evidence
objects each. These 14 structured objects enter human review as `pending`.
Their legacy predecessors remain immutable historical records and are not
silently promoted, overwritten, or deleted.

### 17.16 Review-driven parser correction

Human review of the parser 1.1 replay accepted 2 of 14 objects and rejected 12.
The rejected corpus exposed five deterministic boundary failures: page
furniture, back matter, cross-subsection aggregation, incomplete page-ending
sentences, and short numeric claim fragments.

Parser 1.2 converts those review findings into fail-closed extraction rules:

- journal headers, footers, and publication metadata terminate a segment;
- supporting information, author contributions, references, discussion, and
  other back matter bound the preceding scientific section;
- survey recruitment, data collection, and the evaluated findings subsection
  form explicit scientific boundaries;
- page-ending text is retained only through the last complete sentence; and
- short fallback fragments such as `We find that 26.` are not emitted.

Regression tests cover both contaminated section boundaries and truncated
claim fragments. The 2026-07-19 parser 1.2 replay produced 13 candidates:
12 passed structured human review and one navigation-only sentence was
rejected. No research evidence remained pending, no review projection was
inconsistent, and the immutable parser 1.1 decisions remained historical.

### 17.17 Reviewed-evidence intake and graph admission

The parser 1.2 evidence set was admitted through the canonical indexer path,
not by direct database mutation. Two immutable intake manifests bind the
accepted evidence selection, extraction-manifest hash, actor, decisions,
graph content hash, and intake provenance:

- DOI `10.1371/journal.pone.0268993`: 6 requested, 6 admitted, 7 graph nodes,
  and 14 graph edges; and
- DOI `10.1371/journal.pone.0319334`: 6 requested, 6 admitted, 7 graph nodes,
  and 10 graph edges.

The admission gate resolved the current structured review projection for each
requested object. All 12 accepted parser 1.2 evidence objects became knowledge
nodes, no rejected parser 1.2 object became a node, and every evidence-sourced
edge was persisted with accepted review status and provenance. The replayable
operator is `Scripts/intake_parser_v12_plos_evidence.ps1`.

### 17.18 Theory support deduplication and human authority

Theory construction over the two admitted graphs initially counted two graph
edges from the same evidence object and quote as two supporting observations.
The builder now deduplicates support by graph ID, evidence object ID, and quote
hash, retaining a deterministic representative edge. Regression coverage
proves that alias edges cannot inflate `support_count`.

The corrected bundle produced three proposals with one independent supporting
evidence item each. Structured human review rejected all three because they
were source conclusions or descriptive findings rather than explanatory
theoretical abstractions supported across independent evidence. The final
snapshot contains three review events, zero accepted proposals, three rejected
proposals, and zero proposals left unreviewed. Evidence and graph acceptance
were not reversed by theory rejection. The review operator is
`Scripts/review_plos_theory_bundle.ps1`.

### 17.19 Targeted evidence expansion after theory rejection

Rejection of the initial single-source theory proposals triggered a bounded
discovery expansion rather than automatic theory promotion. A documented
contract queried OpenAlex and Crossref for open-science data-sharing
incentives, barriers, attitudes, and policy compliance. The run enumerated 50
provider observations, deduplicated them to 49 scholarly records, collected
metadata, and preserved two metadata conflicts for review.

Title and source screening selected three independent PLOS studies for
full-text processing: a qualitative interview study, a survey of qualitative
researchers, and a systematic literature review. A fourth citation-advantage
candidate was not acquired because its enumerated OpenAlex record did not
provide a PDF URL. The systematic review required a separate immutable
type-compatible contract; screening now binds the document to the newest
matching query family and source definition, preventing an older contract for
the same DOI from controlling the decision.

Parser 1.2 produced nine candidates across the three eligible studies.
Structured review accepted five and rejected four contaminated, flattened, or
misclassified segments. Three intake manifests created three independent
graphs from the five accepted objects. No rejected object became a knowledge
node, no targeted object remained pending, and the current-review projection
remained consistent. Operational scripts are:

- `Scripts/discover_open_science_theory_evidence.ps1`;
- `Scripts/acquire_targeted_open_science_evidence.ps1`;
- `Scripts/process_open_science_systematic_review.ps1`;
- `Scripts/review_targeted_open_science_evidence.ps1`; and
- `Scripts/intake_targeted_open_science_evidence.ps1`.

### 17.20 Fail-closed cross-study theory synthesis

Theory synthesis over more than one graph now uses an explicit independence
gate. A result, limitation, or conclusion may inform a candidate only when it
participates in an asserted `supports` relationship, retains accepted review
provenance, and contains an informative scientific statement. Repeated edges
from the same graph, evidence object, and quote remain one supporting
observation.

A proposition is emitted only when the normalized statement is supported by
at least two distinct graph IDs and two distinct evidence object IDs. The
system expresses the retained statement as a cross-study proposition and
leaves its review state as `proposed`; it cannot promote the proposition
without a subsequent attributable human decision. Unsupported limitations,
generic node labels, single-study claims, and merely related but non-equivalent
statements fail closed.

The regression suite contains 25 passing theory tests, including supported
result eligibility, unsupported limitation exclusion, duplicate support
suppression, and the two-graph/two-object independence requirement. The
operational run over the three targeted PLOS graphs created verified bundle
`theory-bundle-e38bc3fded9bd450cbdb76e3` with content hash
`710ff729c24c58efe8800b6107ec2c0644d242b8fc8d819b8d27e7e60698885a`.
It emitted zero proposals because the five accepted evidence objects do not
yet contain an equivalent explicitly supported statement across two
independent graphs. This zero result is the required scientific behavior:
ResearchOS records the synthesis attempt without fabricating a theory.

### 17.21 Semantic relation admission boundary

The graph layer now contains the complete SGF-030 relation vocabulary and a
fail-closed construction contract for explicit provenance-bound assertions.
All referenced source, target, and provenance objects must be admitted
evidence; unsupported references and self-relations are rejected. Intakes
without explicit relations retain their existing deterministic graph
identities.

Semantic relations now follow `proposed -> accepted | rejected`. A discoverer
creates a content-addressed proposal; a different authenticated reviewer
records an immutable accepted or rejected event; and the latest verified
snapshot provides current state. Accepted relations can later be rejected
without deleting either decision. A broken review-state chain, proposer
self-approval, unsupported relation type, duplicate intake selection, stale
evidence admission, or unaccepted relation fails closed.

Knowledge intake schema 1.1 records the exact accepted relation IDs used to
construct a graph. Each relation must belong to the same extraction and all
its referenced objects must be among the evidence admitted by that intake.
No co-occurrence inference is permitted. Intakes without relations remain
schema 1.0 compatible.

The focused graph, intake, ontology, theory, and API suites contain 84 passing
tests. Coverage includes proposal replay, independent review, snapshot
restoration, accepted-only intake, accepted-to-rejected reversal, review-chain
integrity, relation vocabulary boundaries, and end-to-end authenticated API
admission.

### 17.22 Semantic relation dependency invalidation

Every relation-bearing intake appends an immutable admission event to the
relation lifecycle. The event binds relation ID, graph ID, intake ID, indexer,
and occurrence time. These events are restored from verified snapshots after
service restart and provide the relation-to-graph dependency projection.

Graph current-state now combines the canonical evidence ledger with semantic
relation state. If any admitted relation is no longer `accepted`, the graph
projects as `superseded` while its graph and intake snapshots remain immutable.
The relation ID and current state are exposed in graph lifecycle and theory
dependency projections.

Propagation continues downstream:

- theory construction rejects a superseded graph;
- an existing theory bundle becomes non-current;
- validation reports cease to be active for the current dependency state;
- revalidation is rejected until dependencies are current; and
- publication preview and readiness fail their current-dependencies check.

The complete focused suite contains 85 passing tests. It covers restart
recovery of graph admissions, accepted-to-rejected propagation, preservation
of the older evidence-error contract, snapshot-only compatibility, theory
construction blocking, validation invalidation, and publication-readiness
failure.

### 17.23 Provenance-complete semantic relation review queue

The authenticated semantic relation review queue projects one extraction at a
time without changing scientific state. Discoverers, reviewers, and auditors
can inspect:

- every currently accepted object, its type, exact coordinates, statement,
  extraction method, parser version, and manifest hash;
- the attributable evidence review event, provenance ID, assessment, and
  assessment hash;
- every semantic relation proposal with its source, target, provenance object,
  state, reviews, and admission history;
- coverage of `population`, `variable`, `measurement`, and `limitation`
  annotations; and
- explicit blockers that prevent a defensible relation proposal.

The queue does not infer a relation or convert a missing annotation into an
accepted object. The focused graph, intake, ontology, theory, and API suites
remain at 85 passing tests after provenance-context coverage was added.

Operational evaluation of the five accepted targeted evidence objects created
three queues:

- `extraction-7e80eb1c28ce3ea22d4a173b`: two accepted objects, zero relation
  proposals, and all four structured annotation types missing;
- `extraction-835383e16cda31c453098cf3`: two accepted objects, zero relation
  proposals, and all four structured annotation types missing; and
- `extraction-3bffb1b0c21a6ce4df7d9773`: one accepted object, zero relation
  proposals, all four annotation types missing, and an additional
  two-object relation blocker.

No relation was proposed merely to satisfy workflow completion. The next
scientifically valid operation is a new structured extraction and human review
of population, construct or variable, measurement or outcome, and limitation
objects from the exact source passages.

### 17.24 Structured semantic re-extraction intake

The next operation identified in Section 17.23 is implemented as an
authenticated discoverer action:

`POST /knowledge/extractions/{extraction_id}/semantic-reextractions`

The operation accepts either an explicit subset of accepted evidence object
IDs or, when the subset is empty, all currently accepted objects in the parent
extraction. The evidence-admission gate rejects pending, rejected, unknown, or
otherwise unadmitted sources. The deterministic parser produces exact,
coordinate-bound candidates and persists a schema `1.1` extraction manifest
through the canonical PostgreSQL repository. Identical retries resolve to the
same immutable manifest and hash.

The actual data-backed run produced:

- `extraction-aef6f19024c52d04de262457`, derived from
  `extraction-7e80eb1c28ce3ea22d4a173b`: three objects
  (two population and one limitation);
- `extraction-888adf6b1db2130f41ac8037`, derived from
  `extraction-835383e16cda31c453098cf3`: 28 objects
  (eight population, eleven variable, eight measurement, and one limitation);
  and
- `extraction-ea43bc19d859edbd58a51f8e`, derived from
  `extraction-3bffb1b0c21a6ce4df7d9773`: 19 objects
  (nine population, two variable, seven measurement, and one limitation).

PostgreSQL contains all 50 derived objects and projects all 50 as `pending`.
Manifest integrity verification passed for every extraction, and a second
identical request returned the same manifest hash in all three cases. No
derived object was automatically reviewed, accepted, related, indexed, or
promoted into a theory. The next authority-bearing operation is human evidence
review of these candidates for citation fidelity, preserved context,
relevance, confidence, and epistemic classification.

That human review was subsequently completed against the frozen 50-object
packet. The human authority approved 36 accept and 14 reject recommendations,
after which the authenticated reviewer workflow wrote 50 immutable review
events bound to both statement and extraction-manifest hashes. PostgreSQL
projects 36 objects as accepted and 14 as rejected; all 50 stored states agree
with the current hash-bound review projection. Review created zero knowledge
nodes, preserving the separation between evidence authority and indexer
admission.

### 17.25 Explicit semantic relation proposal

Following structured evidence review, the discoverer evaluated all 36 accepted
objects under the no-inference rule. Three provenance-bound proposals were
defensible:

- `semantic-relation-b2f7d38f7b7fbd8915ff3875`, a `has_limitation`
  assertion within `extraction-888adf6b1db2130f41ac8037`;
- `semantic-relation-9ba7d3896ae0638bb5ef6c0e`, a `measures` assertion
  within `extraction-ea43bc19d859edbd58a51f8e`; and
- `semantic-relation-cd9b1589289a15f2cd80deaa`, a second `measures`
  assertion within `extraction-ea43bc19d859edbd58a51f8e`.

All three remain `proposed`. No relation was created for
`extraction-aef6f19024c52d04de262457`, because its accepted objects do not
support an explicit relation in the implemented vocabulary. Human relation
review and indexer admission remain separate subsequent authority boundaries.

The human authority subsequently approved the frozen three-relation packet.
The authenticated reviewer, distinct from the discoverer, recorded one
accepted review for each relation. The current projection contains zero
proposed, three accepted, and zero rejected relations. All three retain zero
graph admissions, so review did not bypass the independent indexer boundary.

### 17.26 Structured evidence and relation graph intake

The authenticated indexer admitted the reviewed structured evidence in three
extraction-bounded operations:

- `intake-7305fcd8e3692a6d39615f24` produced
  `graph-bb59192c7b3c0706e5cbfe6d` from two accepted population objects and no
  semantic relation;
- `intake-0877683e0dd244eb7ec3005f` produced
  `graph-ea24fd3bf004e01a3986cd80` from nineteen accepted evidence objects and
  the accepted `has_limitation` relation; and
- `intake-b19f65bd1f1a211faa903c99` produced
  `graph-b9e1f372aa7185404c5548f7` from fifteen accepted evidence objects and
  the two accepted `measures` relations.

All three intake and graph manifests passed integrity verification. Together
they contain three source nodes, 36 evidence nodes, 36 provenance edges, and
three reviewed semantic edges. Each semantic relation has exactly one
immutable graph-admission event linked to its graph, intake, indexer, and
timestamp.

### 17.27 Cross-study theory alignment gate

The three current structured graphs were evaluated together by the verified
cross-study theory builder. Although all concern research data, their accepted
objects address different bounded propositions: interviewees' data needs, a
systematic synthesis of sharing and use drivers and inhibitors, and survey
measurements of sharing experience and attitude.

No accepted passage explicitly supports, contradicts, or extends a proposition
from another graph. The builder therefore created
`theory-bundle-5d3969d8d234f8188c5240e1` with three graph dependencies and zero
theory proposals, competing theories, reviews, or alignments. Its immutable
snapshot passed integrity verification.

This zero-proposal outcome is the required fail-closed behavior. Broad thematic
similarity cannot substitute for proposition equivalence, explicit `supports`
edges, or independent cross-study evidence.

After targeted acquisition, review, annotation, relation review, and graph
intake, the theory gate was repeated on the two most relevant independent
structured graphs. It produced
`theory-bundle-5c3a0c3cb880a096a234f667`, with two graph dependencies and zero
proposals. Both graphs contain reviewed population, variable, measurement, and
`measures` assertions, but neither supplies an eligible result, conclusion, or
limitation node with an explicit `supports` edge. The gate correctly refuses
to reinterpret measurement as proposition support.

The remaining blocker is therefore a graph-contract boundary: ResearchOS
needs a provenance-safe, reviewer-governed way to bind accepted parent results
to their accepted derived annotations, or an equivalent reviewed proposition
support contract. This extension must preserve extraction provenance and
cannot infer support from shared documents or lexical similarity.

### 17.28 Reviewer-governed cross-study proposition contract

The equivalent reviewed proposition-support contract is now operational.
Creation requires at least two accepted RESULT, CONCLUSION, or LIMITATION
objects drawn from at least two verified graphs and two distinct source
documents. Each reference records its graph, evidence object, document,
verbatim quote hash, node type, and support stance.

The proposition lifecycle is `proposed -> accepted | rejected`. Its immutable
snapshot verifies the synthesized statement, evidence bindings, proposer,
rationale, and review history. The proposer cannot review their own
proposition. Review and theory generation both revalidate current evidence
admission and graph lifecycle, so a stale or invalidated dependency fails
closed. Only an independently accepted proposition can be converted into a
theory bundle.

Graph restart recovery now verifies each stored raw graph hash before typed
reconstruction. Hash-valid historical graphs without complete accepted review
provenance remain preserved but are excluded from current graph authority;
hash corruption still prevents startup.

The first operational candidate,
`cross-study-proposition-93c9eec35dfbac882b061a1a`, binds two accepted results
from two independent source documents. It remains `proposed`, with zero
reviews and zero theory bundles, until the human-review packet is decided.
Focused contract and persistence tests pass, and the deployed API recovered
the same proposition identifier and content hash after restart.

## 18. Verification plan

Tests must cover:

- every permitted and forbidden transition;
- stale expected state and concurrent updates;
- missing actor, rationale, provenance, or content hash;
- idempotent replay and conflicting replay;
- direct ledger mutation;
- upstream invalidation propagation;
- publication immutability and corrected edition behavior;
- evidence reversal with historical preservation;
- terminal archive behavior;
- role and separation-of-duties requirements; and
- UI/backend action consistency.

## 19. Definition of Done

SGF-040 is complete as an operational lifecycle standard when:

1. common lifecycle language is distinct from epistemic status;
2. each implemented object family has a bounded lifecycle profile;
3. transition events have a shared minimum contract;
4. correction, retraction, invalidation, and supersession are distinct;
5. dependency propagation is explicit;
6. concurrency and stale-state safety are defined;
7. existing enforcement and extensions are separated; and
8. product and repository lifecycle projections use the same transition
   contract.
