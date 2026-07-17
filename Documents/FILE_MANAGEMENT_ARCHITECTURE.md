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

