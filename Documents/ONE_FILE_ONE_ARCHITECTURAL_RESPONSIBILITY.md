# One File — One Architectural Responsibility (OFAR)

## Status

- Document status: initial evidence-based audit and staged governance baseline
- Classification: engineering rule, File Management Architecture extension,
  and Architecture Engine review signal
- Owner: Architecture Governance
- Authority: project owner
- Recorded: 2026-07-18
- Source revision: `335a63f`
- Enforcement: report-only; no blocking law or automated refactoring

## Principle

Each production file should have one primary architectural responsibility, one
architectural home, one owner, and one primary reason to change. If a file
acquires a second independent reason to change, it must be reviewed for
separation through evolutionary, compatibility-preserving refactoring.

OFAR is responsibility-based, not line-count-based. A long file can comply
when all content changes for the same architectural reason. A short file can
violate OFAR when it mixes independent domain, execution, persistence,
transport, orchestration, validation, or presentation responsibilities.

The supporting rules are:

1. A filename reflects its primary responsibility.
2. A file is not a temporary home for unclassified functions.
3. Generic utility files are avoided.
4. Cross-layer mixing requires an approved contract and rationale.
5. Strategic files remain traceable to capability, contract, owner, and tests.
6. Separation follows responsibility rather than size.
7. Refactoring preserves public and persistence compatibility.
8. General cleanup requires its own approved sprint.
9. A defect caused by mixed responsibility receives a regression test.
10. Automated metrics are review signals, never automatic proof of violation.

## Dependency verification

The audit inspected:

- `Documents/LONG_TERM_ENGINEERING_CHARTER.md`;
- `Documents/FILE_MANAGEMENT_ARCHITECTURE.md`;
- `Documents/FILE_MANAGEMENT_SAFETY_BASELINE.md`;
- `.github/researchos/repository-policy-v1.json`;
- the Architecture Graph, scanner, semantic extractors, law registry, public
  namespace validator, policy registry, File Registry, traceability builder,
  placement/naming verifier, and repository health capability;
- active Kernel, Runtime, Architecture, Scientific Knowledge, Discovery,
  repository, persistence, orchestration, router, worker, product-session, and
  test packages;
- static AST structure, dependency imports, public methods, test references,
  file size as context only, and file-change frequency over the latest 100
  commits.

Existing canonical foundations already provide:

- path-based ownership, architectural home, placement, naming, and lifecycle;
- deterministic file identity and content hashes;
- file-to-capability traceability in the existing Architecture Graph;
- report-only verification and health evidence;
- compatibility review before movement or removal; and
- isolated, reversible repository evolution.

No existing canonical law ID defines OFAR. Current executable law identifiers
use established categories such as dependency and public-API rules, while FMA
identifiers describe Repository Management capabilities and policies.
Therefore this audit does not invent an `ALA-FILE-*` or other new prefix.

## Governance position

OFAR is adopted in three compatible roles:

1. **Engineering rule** — it guides design and review of every new or changed
   production file.
2. **FMA extension** — ownership, naming, traceability, dependency, and test
   evidence are resolved through existing Repository Management authorities.
3. **Architecture Engine review signal** — deterministic heuristics may
   identify files that require human review.

OFAR is not currently a blocking Architecture Law. Current semantic evidence
cannot reliably prove that two symbols have independent reasons to change.
Blocking enforcement before a reviewed baseline would create false positives
and encourage cosmetic file splitting.

The following remain invariant:

- existing canonical code is the Single Source of Truth;
- a model does not become a repository;
- a repository does not become a workflow orchestrator;
- a transformer does not perform scientific reasoning;
- an orchestrator coordinates but does not become canonical persistence;
- public namespaces, constructors, enums, APIs, event payloads, schemas, and
  serialization contracts do not change silently; and
- no automated OFAR finding authorizes a move, split, removal, or compliance
  verdict.

## Audit method and limitations

Status meanings:

- **PASS** — one primary architectural responsibility is supported by current
  structure, dependency direction, ownership, and focused tests.
- **PARTIAL** — the primary responsibility is identifiable, but the file also
  contains related concerns or has more than one plausible reason to change.
- **VIOLATION** — evidence shows multiple independent architectural reasons to
  change or multiple layer responsibilities in one file.
- **REVIEW REQUIRED** — static evidence is insufficient for a safe verdict.

Risk reflects change amplification and architectural safety, not file length.
No item was classified Critical: the audit found no new active bypass,
duplicate canonical authority, scientific safety failure, or corruption path.
The audit is strategic rather than exhaustive and does not claim
repository-wide compliance.

## Audit summary

| Status | Count |
| --- | ---: |
| PASS | 3 |
| PARTIAL | 9 |
| VIOLATION | 7 |
| REVIEW REQUIRED | 1 |
| Total inspected | 20 |

| Risk | Count |
| --- | ---: |
| Critical | 0 |
| High | 9 |
| Medium | 8 |
| Low | 3 |

## Strategic file map

| Path | Architectural home and owner | Current responsibility and reasons to change | Dependencies and public contracts | Tests | Status | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `AI-Gateway/app/kernel/contracts/capability.py` | Kernel / Kernel contracts | Defines the capability protocol; changes only with the Kernel contract | Typing only; `Capability` public contract | Kernel public API tests | PASS | Low | Retain |
| `AI-Gateway/app/runtime/retry_policy.py` | Runtime / Runtime Engine | Defines retry-policy behavior | Typing only; `RetryPolicy` public contract | Runtime retry tests | PASS | Low | Retain |
| `AI-Gateway/app/architecture/repository/traceability_graph_builder.py` | Architecture / Repository Management | Projects repository evidence into the existing Architecture Graph | Architecture models and repository contracts; builder public namespace | Repository traceability and health tests | PASS | Low | Retain |
| `AI-Gateway/app/main.py` | Application composition | Composes API, settings, readiness, and service dependencies | Public application startup boundary | Main, readiness, router, and API regression suites | PARTIAL | High | Audit composition-only invariant before any extraction |
| `AI-Gateway/app/settings.py` | Application configuration | Centralizes many subsystem settings | Environment contract used across runtime and operations | Settings plus broad integration tests | REVIEW REQUIRED | High | Build a setting-to-owner inventory before deciding separation |
| `AI-Gateway/app/architecture/pipeline_service.py` | Architecture / Governance pipeline | Stores pipeline artifacts and orchestrates scan, laws, compliance, review, and ARC generation | Graph, governance, persistence, filesystem; `ArchitecturePipelineService` | Architecture API, observability, transactional persistence | PARTIAL | High | Separate artifact-store review from orchestration in a future sprint only if contracts remain stable |
| `AI-Gateway/app/architecture/repository/evolution_recovery.py` | Architecture / Repository Evolution | Models, verifies, and plans recovery decisions | Evolution execution and verification contracts | Repository evolution lifecycle tests | PARTIAL | Medium | Consider model/planner separation when this surface next changes |
| `AI-Gateway/app/router/knowledge.py` | Transport / Scientific Knowledge API | Exposes discovery, acquisition, evidence, graph, theory, validation, publication, monitoring, and semantic routes | FastAPI and multiple scientific capability contracts; large public HTTP surface | Knowledge API and composed-router tests | VIOLATION | High | Split by stable capability router while preserving paths and exported router composition |
| `AI-Gateway/app/router/knowledge_workspace.py` | Transport / Product workspace | Defines request models, background translation state, object intelligence, work queue, graph, and workspace routes | FastAPI, Pydantic, service dependencies; workspace HTTP surface | Knowledge API workspace and translation regressions | VIOLATION | High | Separate translation job transport/state from workspace read routes |
| `AI-Gateway/app/knowledge/theory_pipeline.py` | Scientific Knowledge / Theory orchestration | Orchestrates theory building, review, alignment, translation, calibration, gaps, validation, and publication | Theory, validation, publication, gap, persistence, and admission capabilities | Theory builder, validation, publication, gap, API tests | VIOLATION | High | Extract one capability at a time behind the existing facade |
| `AI-Gateway/app/knowledge/ingestion_pipeline.py` | Scientific Knowledge / Ingestion orchestration | Coordinates the canonical discovery-to-intake sequence | Discovery, acquisition, inspection, screening, extraction, graph, intake repositories | Knowledge intake, discovery, extraction, graph, API tests | PARTIAL | Medium | Retain as workflow facade; audit stage adapters before adding responsibilities |
| `AI-Gateway/app/knowledge/service.py` | Scientific Knowledge / Service facade | Delegates ingestion, monitoring, translation, theory, publication, semantic, and workspace operations | Multiple pipelines and repository services; major application service contract | Knowledge API plus subsystem regressions | VIOLATION | High | Introduce capability services behind a compatibility-preserving facade |
| `AI-Gateway/app/knowledge/models.py` | Scientific Knowledge / Discovery representation | Contains discovery source, question, contract, query, provider, record, and run models | Dataclasses and enums; several serialized contracts | Discovery and API contract tests | PARTIAL | Medium | Group by contract family only when schema compatibility is proven |
| `AI-Gateway/app/knowledge/repositories/postgres.py` | Scientific Knowledge / PostgreSQL persistence | Implements core persistence across discovery, metadata, citation, representations, inspection, and screening and assembles mixins | Psycopg boundary via repository core; canonical persistence port | Repository, API, storage, and integration tests | VIOLATION | High | Continue extracting domain-specific mixins; preserve one canonical repository facade |
| `AI-Gateway/app/knowledge/repositories/postgres_evidence.py` | Scientific Knowledge / Evidence persistence | Persists evidence, review admission, extraction manifests, and canonical graph | Evidence, intake, graph, and discovery normalization contracts | P0 evidence, graph, API, and PostgreSQL integration tests | PARTIAL | High | Review evidence and graph persistence boundaries before the next schema change |
| `AI-Gateway/app/knowledge/discovery/providers.py` | Scientific Knowledge / Provider integrations | Defines provider protocols, HTTP base, and three independently evolving providers | Requests and discovery contracts; provider interfaces | Literature discovery and provider tests | VIOLATION | Medium | Move providers one at a time into provider-specific modules behind unchanged exports |
| `AI-Gateway/app/workers/main.py` | Runtime / Worker execution | Handles heartbeat, stop signals, claiming, retry, failure disposition, isolated execution, timeout, and process loop | Multiprocessing, signals, queue, metrics; worker entrypoint | Worker lifecycle, retry, metrics, and resilience tests | PARTIAL | High | Extract lifecycle or execution supervision only with entrypoint regression coverage |
| `AI-Gateway/app/product/sessions.py` | Product / Human workspace sessions | Handles authentication, sessions, administration, audit reads, and recovery status | PostgreSQL, password hashing, authentication, restore attestation; session manager contract | Session/API and recovery-status tests | VIOLATION | High | Separate recovery projection from session administration first |
| `AI-Gateway/app/knowledge/tests/test_knowledge_api.py` | Scientific Knowledge tests | Tests discovery through workspace, evidence, graph, translation, monitoring, and product APIs | Many routers, repositories, fakes, and public contracts | It is the test aggregation itself | VIOLATION | Medium | Split by public capability without weakening end-to-end coverage |
| `AI-Gateway/app/architecture/tests/test_repository_evolution.py` | Architecture tests / Repository Evolution | Tests the full FMA-008 plan-to-closure lifecycle | Repository evolution public namespace | Covers every FMA-008 stage and bypass guard | PARTIAL | Medium | Keep lifecycle integration coverage; add focused files only as stages change |

## High-risk findings

### Scientific API transport concentration

- **Path:** `AI-Gateway/app/router/knowledge.py`
- **Current responsibility:** public scientific HTTP transport.
- **Conflicting responsibility:** one module owns independently changing route
  families from discovery through publication.
- **Architectural home:** Transport / Scientific Knowledge API.
- **Owner:** Scientific Knowledge Subsystem.
- **Risk:** High; path or dependency changes have broad public blast radius.
- **Public contract impact:** all existing paths, roles, request/response
  models, and router composition must remain unchanged.
- **Test coverage:** broad knowledge API and composed-router regression tests.
- **Recommendation:** capability-router extraction in small compatibility
  sprints, beginning with the least coupled route family.

### Theory workflow concentration

- **Path:** `AI-Gateway/app/knowledge/theory_pipeline.py`
- **Current responsibility:** theory construction orchestration.
- **Conflicting responsibility:** alignment, translation, calibration,
  validation, gap detection, and publication have independent reasons to
  change.
- **Architectural home:** Scientific Knowledge / Theory orchestration.
- **Owner:** Scientific Knowledge Subsystem.
- **Risk:** High; scientific review and publication behavior share one change
  surface.
- **Public contract impact:** the current `KnowledgeTheoryPipeline` facade and
  persisted schemas must remain readable.
- **Test coverage:** theory, validation, publication, gap, translation,
  calibration, and API suites.
- **Recommendation:** extract one capability service at a time behind the
  existing facade; never move scientific admission guards as incidental work.

### Scientific service facade concentration

- **Path:** `AI-Gateway/app/knowledge/service.py`
- **Current responsibility:** application-facing scientific service.
- **Conflicting responsibility:** ingestion, monitoring, object translation,
  theory, publication, semantic search, and workspace read models evolve
  independently.
- **Architectural home:** Scientific Knowledge / Service facade.
- **Owner:** Scientific Knowledge Subsystem.
- **Risk:** High; it is among the most frequently changed production files in
  the last 100 commits.
- **Public contract impact:** routers and tests construct
  `KnowledgeDiscoveryService` directly.
- **Test coverage:** knowledge API and focused capability suites.
- **Recommendation:** preserve the class as a compatibility facade while
  delegating to focused capability services.

### Canonical PostgreSQL concentration

- **Path:** `AI-Gateway/app/knowledge/repositories/postgres.py`
- **Current responsibility:** canonical scientific persistence facade.
- **Conflicting responsibility:** discovery, metadata, citation,
  representation, inspection, and screening persistence coexist in its core.
- **Architectural home:** Scientific Knowledge / Persistence.
- **Owner:** Scientific Knowledge Subsystem.
- **Risk:** High; unsafe separation could create duplicate authority or partial
  transactions.
- **Public contract impact:** `PostgresScientificDataRepository` remains the
  canonical repository facade.
- **Test coverage:** repository, storage, API, and PostgreSQL integration
  suites.
- **Recommendation:** continue the existing mixin pattern only after
  transaction and constructor compatibility verification.

### Session and recovery projection mixing

- **Path:** `AI-Gateway/app/product/sessions.py`
- **Current responsibility:** human session and administration lifecycle.
- **Conflicting responsibility:** recovery-readiness projection depends on
  independent restore evidence and attestation concerns.
- **Architectural home:** Product / Human workspace.
- **Owner:** Product capability.
- **Risk:** High; authentication changes and recovery-evidence changes should
  not share one file.
- **Public contract impact:** `WorkspaceSessionManager` and recovery status
  response compatibility must remain stable.
- **Test coverage:** session/API and recovery-status regressions.
- **Recommendation:** first remediation candidate after public caller and
  constructor audit.

## Candidate automated checks

| Signal | Possible implementation | False-positive risk | Position |
| --- | --- | --- | --- |
| Generic filename | Match `utils`, `helpers`, `common`, `misc`, overly broad `manager` or `service` | High: a facade can be legitimate | Report-only |
| Multiple architectural symbol roles | AST classify models, repositories, validators, routers, and orchestrators in one module | Medium to high | Requires reviewed semantic-role vocabulary |
| Cross-layer imports | Compare AST imports with canonical ownership and dependency laws | Medium: composition roots are legitimate exceptions | Extend existing Architecture Graph evidence |
| Multiple public contracts | Count exported constructors, enums, routes, schemas, and CLI commands | Medium: cohesive contract families exist | Report-only |
| Missing focused test | Resolve production file to explicit unit/contract/integration tests | High: tests may cover behavior through a public facade | Finding must include coverage evidence |
| Ambiguous ownership | Resolve file against FMA ownership policies | Low | Existing policy registry can provide evidence |
| Excessive fan-in/fan-out | Use Architecture Graph edges with capability context | Medium | Thresholds require a measured baseline |
| High change frequency | Bind Git history counts to file identity | High: active stable facades change often | Review signal only |
| Mixed persistence and transport | Combine symbol roles and dependency edges | Medium | Human confirmation required |
| Multiple capability ownership | Compare traceability relationships for one file identity | Low to medium | Fail closed on conflicting declarations, not on mere usage |

The first automated increment should emit a deterministic, content-addressed,
report-only OFAR review-candidate report. It must not assign PASS or VIOLATION
from line count, symbol count, fan-out, or churn alone.

## Remediation roadmap

Each sprint produces one testable deliverable and requires separate approval.

### OFAR-001 — Audit baseline and governance position

- **Deliverable:** this document and its documentation index entry.
- **Expected files:** governance documentation only.
- **Tests:** link, path, status, and diff validation.
- **Compatibility:** no runtime or public-contract change.
- **Rollback:** revert the documentation commit.

### OFAR-002 — Report-only candidate contract

- **Deliverable:** immutable OFAR signal and report models.
- **Expected files:** Architecture Repository Management models and tests.
- **Tests:** determinism, provenance, tamper rejection, explicit unknown state.
- **Compatibility:** no blocking law and no file mutation.
- **Rollback:** remove the unconsumed report capability.

### OFAR-003 — Read-only semantic signal collector

- **Deliverable:** AST, ownership, dependency, public-contract, and test
  evidence for selected tracked Python files.
- **Expected files:** scanner/collector plus focused tests.
- **Tests:** safe path handling, deterministic output, known false positives,
  no imports or execution of inspected code.
- **Compatibility:** report-only; no Architecture Graph authority replacement.
- **Rollback:** disable the collector without changing tracked files.

### OFAR-004 — Human review baseline

- **Deliverable:** reviewed dispositions for candidate findings and documented
  exceptions.
- **Expected files:** versioned governance artifact and documentation.
- **Tests:** provenance, reviewer attribution, lifecycle, and content hash.
- **Compatibility:** no automated refactoring or CI blocking.
- **Rollback:** supersede the review artifact; never rewrite history.

### OFAR-005 — Critical safety remediation

- **Deliverable:** one confirmed bypass, duplicate-authority, scientific
  safety, or corruption issue per sprint, if OFAR-004 identifies one.
- **Expected files:** only the affected boundary and focused tests.
- **Tests:** regression, boundary, architecture, and full suite.
- **Compatibility:** facade or adapter preserves callers.
- **Rollback:** revert the focused change or activate its explicit adapter.

### OFAR-006 — Layer-mixing remediation

- **Deliverable:** one reviewed layer boundary per sprint.
- **Priority:** product recovery projection, scientific routers, theory
  capability orchestration, service facade, then repository core.
- **Tests:** public contract and integration coverage before movement.
- **Compatibility:** constructors, imports, routes, schemas, and persistence
  authority remain stable.
- **Rollback:** keep the original facade delegating to the extracted component.

### OFAR-007 — Test and naming maintenance

- **Deliverable:** split one broad test family or rename one confirmed generic
  file per sprint.
- **Tests:** collection parity and public namespace compatibility.
- **Compatibility:** naming changes require import adapters or a migration
  release.
- **Rollback:** restore the previous test aggregation or compatibility module.

Blocking enforcement may be proposed only after OFAR-002 through OFAR-004
produce a reviewed false-positive baseline. It requires a separately approved
Architecture Law position and must use the canonical law-ID convention
available at that time.

## Definition of done

This initial audit is complete when:

- dependency verification and governance positioning are recorded;
- strategic files are mapped with evidence, risk, contracts, and tests;
- no separation is recommended from line count alone;
- candidate checks remain review signals;
- remediation is staged and compatibility-preserving;
- no source code, public API, schema, or runtime behavior changes;
- no law prefix is invented; and
- repository status and validation are reported before commit or push.
