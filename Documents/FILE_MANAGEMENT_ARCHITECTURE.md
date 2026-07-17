# ResearchOS File Management Architecture

## Status

- Working identifier: FMA-000
- Document status: project-owner-accepted working architecture
- Formal ratification status: not defined by current repository governance
- Classification: repository-management architecture
- Owner: Architecture Subsystem
- Architectural position: Architecture Governance Layer / Architecture Engine
- Capability: Repository Management
- Authority: project owner
- Recorded: 2026-07-17
- Change policy: architecture first, audit second, implementation third

`FMA-000` is a working roadmap identifier. The repository does not currently
define a formal FMA identifier family or ratification lifecycle, so this
document does not claim a formally ratified or published status.

## Purpose

ResearchOS does not treat a repository as a collection of unrelated files.
It treats the repository as a versioned, attributable, and verifiable
representation of the system architecture.

The governing principle is:

> A folder is not merely a place to store files. A folder is a physical
> representation of architecture.

Repository structure must make the following properties discoverable:

- architectural position;
- responsibility;
- ownership;
- lifecycle;
- classification;
- traceability; and
- reason for existence.

## Architectural position

Repository Management is a capability of the existing Architecture Engine.
It must extend the canonical Architecture Graph, Architecture Law Engine,
Compliance Engine, Review Engine, and ARC workflow. It must not create a
parallel architecture or compliance authority.

```text
Architecture Governance Layer
    -> Architecture Subsystem
        -> Architecture Engine
            -> Repository Management capability
                -> inventory
                -> classification
                -> ownership
                -> verification
                -> compliance
                -> health
                -> reporting
```

Deterministic code is authoritative for inventory, classification, hashes,
dependency edges, policy evaluation, and compliance results. AI may explain
findings and propose remediation, but it cannot silently change a file's
classification, ownership, compliance status, or waiver.

## Repository knowledge graph

The intended model is richer than `folder -> file`:

```text
Vision
    -> Governance
        -> Subsystem
            -> Engine
                -> Capability
                    -> Module
                        -> File
                            -> Class
                                -> Method
                                    -> Test
                                        -> Compliance
```

This graph should eventually answer:

- Which capability lacks tests?
- Which engine lacks documentation?
- Which capability owns a file?
- Which subsystems are affected by a proposed file change?
- Does a capability remain aligned with roadmap, architecture, governance,
  tests, and compliance?

The existing Architecture Graph currently represents projects, Python modules,
classes, containment, definitions, and imports. FMA extends that graph
incrementally instead of replacing it.

## Target responsibility domains

The long-term logical domains are:

| Domain | Responsibility | Default lifecycle |
| --- | --- | --- |
| `app/` | Runtime source code | deprecate, replace, remove through compatibility review |
| `tests/` | Unit, integration, architecture, compliance, regression, performance, and manual verification | retain with governed replacement |
| `documents/` | Governance, roadmaps, architecture, science, decisions, standards, publication, and history | revise and archive |
| `tools/` | Verifiers, migrations, generators, benchmarks, and analyzers that are not runtime dependencies | version and deprecate |
| `deployment/` | Docker, Compose, Kubernetes, proxy, infrastructure, and operational contracts | migrate and retire |
| `data/` | Raw, canonical, generated, temporary, and cached data according to explicit storage policy | preserve, regenerate, expire, or delete by class |
| `scripts/` | Build, maintenance, release, and cleanup entry points | version and retire |
| `workspace/` | Experiments, scratch data, local work, and debugging output | local-only and deletable |

These are target logical responsibilities, not an authorization to rename or
move the current `AI-Gateway`, `Documents`, `Scripts`, or `deploy` trees.

## Current compatibility baseline

At the time this architecture was recorded:

- the repository contains approximately 429 tracked files;
- approximately 327 tracked files are Python;
- application and most tests are colocated under `AI-Gateway/app`;
- additional tests exist under `AI-Gateway/` and `AI-Gateway/tests/manual`;
- documentation is stored in a flat `Documents/` directory;
- deployment contracts live under `deploy/`;
- scripts live under `Scripts/`;
- imports, Docker build contexts, CI workflows, documentation links, and
  runtime paths depend on that structure; and
- no runtime log, cache, temporary workspace, or compiled Python file is
  intentionally tracked.

Therefore, a mass rename or relocation would be unsafe. Every structural
migration requires an inventory, impact graph, compatibility map, reversible
steps, focused tests, and full compliance verification.

## File classification

Every governed file must have exactly one primary classification:

- Code
- Test
- Document
- Configuration
- Script
- Dataset
- Artifact
- Generated
- Temporary

Secondary attributes may describe language, format, subsystem, engine,
capability, sensitivity, source of truth, or retention policy. Generated and
temporary files must never be presented as canonical source.

## Ownership

Folders and files must not be architecturally anonymous. Ownership is assigned
to a canonical subsystem, engine, or capability rather than merely a person.

Examples:

| Scope | Architectural owner |
| --- | --- |
| runtime implementation | Runtime Engine |
| scientific discovery implementation | Discovery Engine |
| architecture tests | Architecture Engine |
| roadmap documents | Governance capability |
| deployment contracts | Deployment and Operations capability |

Human maintainers may be recorded separately from architectural ownership.
Ownership changes are reviewable architecture changes.

## Lifecycle

Lifecycle depends on classification:

- runtime code is deprecated and removed through compatibility review;
- tests are replaced only with equivalent or stronger verification;
- documents are revised and archived with traceability;
- canonical data follows preservation and migration policy;
- generated data is reproducible and replaceable;
- cache and temporary data may expire;
- workspace content is local-only and deletable; and
- artifacts preserve the provenance required by their governing workflow.

Moving a file does not reset its history, ownership, or traceability.

## Placement policy

Placement rules must be machine-readable and evaluated deterministically.
Illustrative rules include:

- runtime directories may not contain unidentified temporary fixes;
- document domains may not contain runtime Python modules;
- tests may not contain production business logic;
- tools may not become hidden runtime dependencies;
- workspace and temporary content may not enter Git;
- data files may not be placed at repository root without an explicit
  governance exception; and
- exceptions require an owner, rationale, scope, expiry or review condition,
  and immutable review evidence.

Existing files are not retroactively declared invalid until the applicable
policy, compatibility baseline, and migration state have been established.

## Naming policy

Naming must be class-aware, deterministic, and compatible with language and
tooling conventions. Candidate conventions include:

- Python source: `snake_case.py`;
- Python tests: `test_<subject>.py`;
- governance documents: identifier and descriptive title when the identifier
  family is formally defined;
- roadmaps, decisions, and standards: their own governed identifier families;
- generated artifacts: deterministic names derived from canonical identity
  and version.

FMA must not invent `DOC-*`, `RDM-*`, `DEC-*`, or `STD-*` as formal families
without a separate governance definition and migration plan.

## File Registry

The File Registry is a derived, revision-bound inventory. It should not be a
manually maintained list that becomes stale.

Each record should eventually contain:

- stable file identity;
- repository-relative path;
- content hash and source revision;
- primary classification;
- owner, subsystem, engine, and capability;
- lifecycle and status;
- imports and dependants;
- tests and documentation;
- roadmap, architecture-law, and decision relationships;
- generated or canonical status; and
- traceability and compliance evidence.

A stable file identity must survive a verified rename when content and
provenance prove continuity. Identity design remains an FMA-002/FMA-003
contract decision; `FILE-*` is not yet a formal canonical identifier.

## Verification and compliance

Repository verification should detect:

- misplaced or unclassified files;
- unknown ownership;
- naming violations;
- forbidden dependencies;
- generated or temporary leakage;
- missing tests or documentation;
- stale traceability;
- dead, unused, duplicated, or deprecated files;
- unapproved structural changes; and
- policies that could not be evaluated.

Fail-safe semantics from Architecture Governance apply. `ERROR`, `NOT_RUN`,
`NOT_IMPLEMENTED`, or an empty validation set must never be interpreted as
compliant.

The verifier begins in report-only mode. It may become a blocking CI gate only
after policies, baselines, exceptions, and migration plans are accepted and
the existing repository can satisfy them without suppressing legitimate
failures.

## Repository health and dashboard

Repository Health aggregates deterministic findings without replacing their
source validators. The future dashboard should expose:

- code, test, document, configuration, script, dataset, artifact, generated,
  and temporary inventory;
- ownership and capability coverage;
- architecture and dependency compliance;
- test and documentation coverage;
- health findings and accepted exceptions;
- stale or deprecated content;
- change impact; and
- provenance for every displayed result.

An aggregate score must not hide a blocking finding or unknown state.

## Safety invariants

- Existing canonical code remains the single source of truth.
- FMA does not authorize a second Architecture Graph or compliance engine.
- No mass move occurs before dependency and compatibility verification.
- No file is deleted solely because a heuristic marks it unused or duplicate.
- No generated registry becomes a competing manual source of truth.
- Temporary, cached, and workspace data cannot enter canonical history.
- A file move preserves provenance and revision traceability.
- Policy exceptions are explicit, attributable, reviewable, and bounded.
- Unknown classification, ownership, or validation state fails closed when a
  blocking gate is active.
- Repository observations do not automatically authorize implementation
  changes.

## Mandatory implementation checklist

Every FMA deliverable must complete:

1. Dependency Verification
2. Architecture Position
3. Contract Review
4. Domain Invariant Review
5. Safety Review
6. Test Plan
7. Definition of Done

Each sprint produces one focused, testable deliverable. Architecture,
repository, and compliance checks run after implementation. Structural
migrations require a separate project-owner decision.

## Implementation roadmap

| ID | Deliverable | Required result |
| --- | --- | --- |
| FMA-001 | Repository Classification | Revision-bound, read-only inventory and current-state audit without moving files |
| FMA-002 | Repository Policy Registry | Machine-readable ownership, placement, naming, lifecycle, and exception contracts |
| FMA-003 | File Registry | Deterministic file identities, hashes, classification, ownership, and traceability |
| FMA-004 | Placement and Naming Verifier | Evidence-bearing findings, report-only baseline, and controlled activation |
| FMA-005 | Dependency and Traceability Graph | Vision-to-compliance relationships integrated into the Architecture Graph |
| FMA-006 | Repository Health | Missing coverage, staleness, duplication, dead-file, and generated-leakage findings |
| FMA-007 | Repository Dashboard | Provenance-bearing inventory, coverage, compliance, and health views |
| FMA-008 | Repository Evolution | Impact-aware, reversible, verified structural migration workflow |

## FMA-001 implementation traceability

FMA-001 implements read-only repository classification inside the existing
Architecture Engine:

- immutable classification, file-record, and revision-bound inventory
  contracts:
  `AI-Gateway/app/architecture/repository/models.py`;
- deterministic path classification with an explicit `unknown` state:
  `AI-Gateway/app/architecture/repository/classifier.py`;
- injected tracked-file scanning, normalized repository-relative paths,
  byte-level SHA-256 hashes, duplicate rejection, path containment, symlink
  rejection, and change-during-read detection:
  `AI-Gateway/app/architecture/repository/scanner.py`; and
- unit, integration, tamper, safety, and dependency-boundary tests:
  `AI-Gateway/app/architecture/tests/test_repository_inventory.py`.

The implementation does not modify Architecture Graph schema 1.0,
`ArchitectureArtifact`, or the existing `ArchitectureInventory`. It does not
infer ownership, claim compliance, assign `FILE-*` identities, or move any
repository path.

The first read-only working-tree observation, bound to local revision
`5a81753`, classified 436 files:

| Classification | Count |
| --- | ---: |
| Code | 277 |
| Test | 72 |
| Script | 34 |
| Document | 31 |
| Configuration | 21 |
| Artifact | 1 |
| Unknown | 0 |

This observation included the uncommitted FMA-001 implementation and therefore
uses the explicit revision label `working-tree:5a81753`. Its inventory identity
was `repository-inventory:ResearchOS:b6d502615563c4a6`. It is audit evidence,
not a persisted canonical snapshot or compliance decision. A post-commit scan
must produce the final sprint inventory identity.

## FMA-002 implementation traceability

FMA-002 adds an immutable Repository Policy Registry without converting policy
declarations into Architecture Laws or compliance outcomes:

- typed ownership, placement, naming, lifecycle, exception, and content-
  addressed bundle contracts:
  `AI-Gateway/app/architecture/repository/policy_models.py`;
- read-only path resolution with explicit ownership and lifecycle conflict
  errors:
  `AI-Gateway/app/architecture/repository/policy_registry.py`;
- schema compatibility and a verified baseline policy bundle:
  `AI-Gateway/app/architecture/schema.py` and
  `.github/researchos/repository-policy-v1.json`; and
- contract, tamper, conflict, exception-provenance, canonical-bundle,
  dependency-boundary, and schema tests:
  `AI-Gateway/app/architecture/tests/test_repository_policy_registry.py`.

The version 1.0 baseline contains 14 policies: six ownership policies, three
placement policies, one naming policy, and four lifecycle policies. It carries
no active exception. Its content-addressed identity is
`repository-policy:1.0:a778690b312ac90b`.

Policy resolution returns every matching declaration. Conflicting ownership or
lifecycle declarations fail explicitly instead of using file order or
first-match semantics. A repository policy exception requires a known policy,
path scope, rationale, approving actor, approval date, and an expiry or review
condition. Even a valid exception cannot approve an Architecture finding or
produce a compliance `PASS`; those authorities remain with the existing
Compliance and Review Engines.

## FMA-003 implementation traceability

FMA-003 derives a revision-bound File Registry from the verified FMA-001
inventory and FMA-002 policy bundle:

- immutable file identity, governance-state, continuity-event, and registry
  contracts:
  `AI-Gateway/app/architecture/repository/file_registry_models.py`;
- deterministic registry construction, policy attribution, explicit governance
  gaps, and fail-closed continuity validation:
  `AI-Gateway/app/architecture/repository/file_registry_builder.py`;
- exception attribution without compliance waiver:
  `AI-Gateway/app/architecture/repository/policy_registry.py`; and
- identity, revision, rename, conflict, tamper, schema, governance-gap, and
  bypass tests:
  `AI-Gateway/app/architecture/tests/test_file_registry.py`.

An initial identity is content-addressed from the project, first observed path,
and first observed content hash. A file that remains at the same path keeps its
identity across content revisions. A rename is never inferred from matching
content or similarity: identity continuity requires a finalized
`FileContinuityEvent` whose old and new path, hash, revision, actor, rationale,
timestamp, and event hash all verify.

The registry records `assigned`, `partial`, or `unassigned` governance state
instead of inventing missing ownership or lifecycle declarations. Exceptions
remain attributable evidence and do not convert a governance gap or future
compliance finding into a pass. Conflicting policy declarations and ambiguous,
reused, stale, or incomplete continuity claims fail explicitly.

FMA-003 does not persist a generated registry in the repository, change the
Architecture Graph, move files, infer equivalence between distinct files, or
issue a compliance result.

The first read-only working-tree registry observation covered 443 files:

| Governance state | Count |
| --- | ---: |
| Assigned | 298 |
| Partial | 120 |
| Unassigned | 25 |

It was derived from inventory
`repository-inventory:ResearchOS:a70c1e75d1eb0d56` and policy bundle
`repository-policy:1.0:a778690b312ac90b`, producing registry identity
`file-registry:ResearchOS:573241dcadf92d2f`. This is implementation evidence,
not a committed generated registry or a compliance decision. The partial and
unassigned counts are explicit input for later verification work; FMA-003 does
not silently invent missing policy.

## FMA-004 implementation traceability

FMA-004 adds report-only placement and naming verification to Repository
Management:

- immutable policy-evaluation and repository-verification report contracts:
  `AI-Gateway/app/architecture/repository/verification_models.py`;
- placement, extension, naming, temporal-exception, and provenance evaluation:
  `AI-Gateway/app/architecture/repository/placement_naming_verifier.py`; and
- conformance, finding, uncovered-scope, multi-policy, exception, tamper,
  direct-invocation, schema, and dependency-boundary tests:
  `AI-Gateway/app/architecture/tests/test_repository_placement_naming_verifier.py`.

Every evaluation is bound to the file identity, path, content hash, policy
identity and version, source registry, policy bundle, revision, and evaluation
date. All matching policies are evaluated. Missing placement or naming policy
is recorded as `not_evaluated`; it is never silently converted to conformance.
An active exception produces an attributable `excepted` outcome. A future or
expired exception cannot suppress a finding.

The report mode is permanently explicit as `report_only`, and
`is_compliance_decision` is always false. FMA-004 does not construct an
`ArchitectureViolation`, synthesize an `ArchitectureLaw`, register with the
Compliance Engine, alter the Architecture Graph, or activate a blocking CI
gate.

The first read-only working-tree verification evaluated 446 files through 892
domain evaluations:

| Evaluation outcome | Count |
| --- | ---: |
| Naming conforms | 324 |
| Naming not evaluated | 122 |
| Placement conforms | 168 |
| Placement finding | 2 |
| Placement not evaluated | 276 |

No exception was active. Two existing placement findings remain explicit:
`deploy/backup/Dockerfile` and `deploy/stack.env.example` do not use extensions
currently allowed by `FMA-PLACEMENT-DEPLOY-001`. FMA-004 does not weaken the
policy or move those files. The working-tree report identity was
`repository-verification:ResearchOS:703d612b12656c05`; it is transient audit
evidence, not a committed generated report or compliance decision.

## FMA-005 implementation traceability

FMA-005 integrates dependency and repository traceability into the existing
canonical Architecture Graph:

- graph schema 1.1 compatibility and graph-wide uniqueness/referential
  integrity:
  `AI-Gateway/app/architecture/schema.py` and
  `AI-Gateway/app/architecture/models/architecture_graph.py`;
- selected-source scanning that retains repository-relative identities while
  rejecting duplicate, unsafe, escaping, symbolic-link, missing, non-file, and
  non-Python paths:
  `AI-Gateway/app/architecture/scanner.py` and
  `AI-Gateway/app/architecture/graph_builder.py`;
- File Registry, policy, evaluation, ownership hierarchy, and exact
  module-to-file integration:
  `AI-Gateway/app/architecture/repository/traceability_graph_builder.py`; and
- selected-source, compatibility, provenance, hierarchy, tamper, orphan,
  duplicate, and dependency-boundary tests:
  `AI-Gateway/app/architecture/tests/test_repository_traceability_graph.py`.

Architecture Graph 1.0 remains readable and retains its historical identity.
New traceability snapshots use schema 1.1. They extend the same
`ArchitectureGraph`, `ArchitectureNode`, and `ArchitectureEdge` contracts;
FMA-005 does not create a parallel graph.

Every internal Module in a traceability snapshot must match one File Registry
entry by exact repository-relative path. Project traceability metadata binds
the graph to the registry, policy bundle, verification report, source
revision, and evaluation date. Ambiguous Engine-to-Subsystem or
Capability-to-Engine provenance fails closed.

The pre-implementation unrestricted scan discovered 893 Python modules. Only
326 belonged to the then-current tracked registry; 272 came from `build/` and
295 from `tmp/`. The tracked-source boundary removes that contamination rather
than hiding it after graph construction.

The first read-only working-tree schema 1.1 observation produced:

| Traceability measure | Count |
| --- | ---: |
| Files | 448 |
| Internal modules represented by exact file identity | 328 |
| Repository evaluations | 896 |
| Repository policies | 14 |
| Total graph nodes | 2,247 |
| Total graph edges | 5,767 |
| Internal modules from `build/` or `tmp/` | 0 |

Its transient graph identity was `graph:ResearchOS:c5155b3b194e9487`.
The observation includes the uncommitted FMA-005 implementation and is audit
evidence only. No generated graph is committed, no relationship between tests
and source is guessed from names, no roadmap or vision relationship is
invented, and Repository Evaluation remains distinct from Architecture
Compliance.

## FMA-006 implementation traceability

FMA-006 adds deterministic, report-only Repository Health assessment:

- content-addressed health category, outcome, check, and report contracts:
  `AI-Gateway/app/architecture/repository/health_models.py`;
- fail-safe aggregation with registry, policy-evaluation, and graph provenance
  gates:
  `AI-Gateway/app/architecture/repository/health_engine.py`; and
- leakage, governance, policy coverage, duplication, structural test
  presence, unavailable evidence, tamper, serialization, and dependency-
  boundary tests:
  `AI-Gateway/app/architecture/tests/test_repository_health.py`.

Health outcomes are explicit: `observed`, `finding`, `advisory`, and
`not_evaluated`. A report containing any `not_evaluated` category has aggregate
status `INCOMPLETE`; finding counts and affected evidence remain visible.
Repository Health does not produce a score or Architecture Compliance
decision.

Tracked generated or temporary content, unknown classification, incomplete
governance, repository-policy findings, and missing policy coverage are
deterministic findings. Non-empty byte-identical content and capabilities with
code but no owned test file are advisory observations only. Empty files are
excluded from substantive duplicate detection.

Dead-file analysis, staleness, execution or branch coverage, and documentation
coverage remain `not_evaluated` until revision-bound canonical evidence exists.
An absent import edge does not prove a dead file; structural test presence does
not prove execution coverage; a `deprecate` lifecycle policy does not prove
that a file is stale or already deprecated.

The first read-only working-tree assessment covered 451 files and produced:

| Health outcome | Categories |
| --- | ---: |
| Finding | 3 |
| Advisory | 1 |
| Observed | 4 |
| Not evaluated | 4 |

Deterministic findings covered 145 files with partial or unassigned
governance, 347 distinct files outside one or both placement/naming policy
domains, and two existing placement-policy findings. There was no tracked
generated/temporary leakage, unknown classification, active policy exception,
or non-empty exact duplicate. Structural test presence remained advisory for
`Runtime Execution` and `Deployment and Operations`.

The transient working-tree report identity was
`repository-health:ResearchOS:415f891f4767532b`. It is audit evidence only:
no generated health report is committed, no file is moved or deleted, and no
advisory authorizes repository mutation.

## FMA-007 implementation traceability

FMA-007 begins with a backend-first Repository Dashboard projection boundary:

- immutable, content-addressed file, health, and dashboard snapshot contracts:
  `AI-Gateway/app/architecture/repository/dashboard_models.py`;
- fail-closed projection from the canonical File Registry, Repository
  Verification Report, Architecture Graph 1.1, and Repository Health Report:
  `AI-Gateway/app/architecture/repository/dashboard_projector.py`;
- an injected, read-only service boundary that cannot bypass the projector:
  `AI-Gateway/app/architecture/repository/dashboard_service.py`; and
- determinism, provenance, mixed-revision, tamper, schema, dependency, and
  direct-service tests:
  `AI-Gateway/app/architecture/tests/test_repository_dashboard.py`.

The dashboard snapshot projects inventory, ownership hierarchy, governance
coverage, policy and exception references, repository verification outcomes,
architecture node and edge counts, and every explicit health outcome. Each
snapshot carries the exact identifiers and hashes of all four canonical source
artifacts. It cannot combine different projects or revisions.

The aggregate dashboard status preserves fail-safe semantics. Any
`not_evaluated` health category yields `INCOMPLETE`; findings and advisories
remain separately visible. The snapshot is always a read-only projection and
`is_compliance_decision` is always false. It does not calculate a score,
replace a source validator, read the repository filesystem, persist a
competing registry, or authorize repository mutation.

The browser dashboard remains a separate FMA-007 presentation increment. It
must consume this validated service boundary and retain bilingual labels,
provenance drill-down, and explicit unknown states. It must not reconstruct
repository health or compliance in JavaScript.

### FMA-007 runtime publication boundary

The Repository Dashboard runtime source is an immutable artifact bundle managed
by:
`AI-Gateway/app/architecture/repository/dashboard_store.py`.

Each release directory is addressed by the dashboard snapshot SHA-256 and
contains the exact File Registry, Repository Verification Report, Architecture
Graph, Repository Health Report, and Dashboard Snapshot. Publication is
transactional: artifacts are written to an internal staging directory, the
complete release is rehydrated and projected again, and only then is the
content-addressed active pointer replaced atomically.

Restart rehydration rejects missing files, malformed schemas, modified hashes,
mixed provenance, pointer tampering, and an active source revision that does
not equal an injected expected deployment revision. Interrupted internal
staging directories are recovered without deleting immutable releases.
Publishing the same verified bundle is idempotent.

This artifact store is the only FMA-007 filesystem boundary. Dashboard models,
the projector, the read-only service, future API adapters, and browser code
must not read repository files or recompute repository governance. The store
does not discover tracked files, create a File Registry, run repository
verification, or choose which snapshot becomes scientifically or
architecturally authoritative; it only publishes and rehydrates artifacts
already validated by the canonical pipeline.

### FMA-007 administration API and bilingual view

The ResearchOS workspace exposes the active snapshot through the existing
administrator control plane:

- `GET /admin/repository-dashboard` in
  `AI-Gateway/app/router/administration.py`;
- runtime store and service wiring in `AI-Gateway/app/main.py`; and
- the Repository Dashboard panel in the existing Administration view through
  `AI-Gateway/app/product/static/index.html`, `admin.js`, `admin.css`, and
  `i18n.js`.

The endpoint accepts only the existing admin session or Knowledge API admin
Bearer role. Unauthenticated access returns `401`, a non-admin principal
returns `403`, and a missing, stale, incomplete, or invalid active bundle
returns `503`. The endpoint is read-only and returns only a fully rehydrated
dashboard snapshot.

The browser renders inventory and governance counts, explicit health outcomes,
affected counts, and provenance identifiers. `finding`, `advisory`,
`not_evaluated`, and unavailable states remain visually distinct. Missing data
is never rendered as zero, passing, observed, or compliant. Interface labels
and deterministic health summaries follow the global Indonesian/source
language selector; immutable identifiers and hashes remain unchanged.

## FMA-008 implementation traceability

FMA-008 begins with a planning-only Repository Evolution boundary inside the
existing Architecture Engine:

- immutable, content-addressed migration proposals record source revision,
  canonical file-registry identity and hash, file identity, source and target
  paths, content hash, rationale, and human decision provenance;
- every proposed move has a deterministic inverse rollback move;
- unknown identities, stale paths or hashes, occupied targets, duplicate
  targets, incomplete rollback data, and unattributed decisions fail closed;
- proposal artifacts are explicitly non-executable, including after human
  approval; and
- this increment does not move, rename, delete, or write repository files.

Execution remains outside the contract until a later, separately reviewed
increment defines preflight revalidation, transactional application,
post-migration verification, and recovery behavior.

### FMA-008 preflight revalidation

The second FMA-008 increment adds a live, fail-closed preflight boundary:

- an approved plan is revalidated against the current canonical File Registry
  and Architecture Graph;
- source revision, registry identity and hash, policy provenance, source paths
  and content hashes, target availability, rollback completeness, and graph
  currency are recorded as explicit checks;
- changed canonical state produces `stale`, while missing approval or another
  non-staleness safety failure produces `blocked`;
- a fully successful evaluation produces `ready`; and
- every result is immutable, content-addressed, provenance-bearing, and
  explicitly not an execution authorization.

Preflight does not mutate the repository. A future executor must consume a
fresh `ready` result and independently revalidate it at the mutation boundary.

## FMA-000 Definition of Done

- the governing philosophy and architectural position are explicit;
- relationship to the existing Architecture Engine is explicit;
- current repository compatibility baseline is recorded;
- ownership, lifecycle, classification, registry, naming, verification, health,
  dashboard, and knowledge-graph goals are defined;
- safety invariants prohibit premature mass migration;
- FMA-001 through FMA-008 are ordered;
- the document is linked from the root README; and
- no source file or repository directory is moved by FMA-000.

## Decision boundary

Acceptance of this document authorizes FMA-001 dependency verification and
repository classification audit. It does not authorize renaming, moving,
deleting, or mass-registering existing files.
