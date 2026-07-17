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
