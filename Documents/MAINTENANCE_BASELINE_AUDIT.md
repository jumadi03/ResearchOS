# ResearchOS Maintenance Baseline Audit

## Status

- Document status: initial evidence-based maintenance baseline
- Classification: implementation audit and staged maintenance roadmap
- Owner: ResearchOS project
- Authority: project owner
- Recorded: 2026-07-17
- Source charter: `Documents/LONG_TERM_ENGINEERING_CHARTER.md`
- Source revision: `8b045bad0e72a52bcc7b3ea036593bb90e022913`

## Purpose and method

This audit records how the current repository aligns with the 30 rules in the
Long-Term Engineering Charter. It does not claim that documentation alone
enforces a rule and does not authorize repository-wide cleanup.

The audit inspected existing governance, schema compatibility, repository
management, evidence admission, persistence, migrations, provider boundaries,
workers, backup tooling, observability, security controls, deployment
contracts, tests, CI, and long-term vision documents.

Statuses mean:

- **implemented** — current code and tests provide material enforcement across
  the rule's primary risk;
- **partial** — relevant controls exist, but enforcement or coverage is not
  repository-wide;
- **not-yet-evidenced** — the repository does not yet contain sufficient
  implementation or verification evidence.

## Baseline summary

| Status | Count |
| --- | ---: |
| Implemented | 13 |
| Partial | 15 |
| Not-yet-evidenced | 2 |
| Total | 30 |

This distribution is a roadmap input, not a compliance score. Rules differ in
risk and scope, and one missing critical control can matter more than many
implemented low-risk controls.

## Rule-by-rule audit

| Rule | Status | Current evidence | Remaining gap |
| --- | --- | --- | --- |
| 01 Backward Compatibility | Implemented | Central schema policies, readable legacy versions, additive migrations, compatibility tests | Continue caller audits for every future public change |
| 02 Public Contract First | Partial | Public namespaces and contract-focused tests exist | No repository-wide public-contract inventory or deprecated-path register |
| 03 Deprecation Lifecycle | Not-yet-evidenced | Individual compatibility behavior exists | No explicit ACTIVE-to-REMOVED registry with milestones, callers, and migration guides |
| 04 Migration Before Mutation | Implemented | Versioned PostgreSQL migrations and FMA-008 plan/preflight/dry-run/recovery/closure gates | Production migration activation remains deliberately prohibited |
| 05 No Hidden State | Partial | Settings validation, environment templates, PostgreSQL authorities, content-addressed artifacts | Environment/state ownership and cache invalidation are not yet catalogued repository-wide |
| 06 Deterministic Core | Implemented | Deterministic governance, admission, graph, theory, hashing, and explicit provider provenance | Broader replay metadata for every network/AI path remains incremental work |
| 07 Reproducible Environment | Partial | Python runtime range, pinned direct dependencies, container definitions, environment templates, migrations, bootstrap docs | No resolved transitive dependency lock or reproducible-build attestation |
| 08 Dependency Discipline | Partial | Direct dependencies are pinned and CI runs `pip-audit` | No mandatory dependency decision template covering license, transitive risk, and exit strategy |
| 09 Replaceability | Implemented | Provider interfaces, registries, repository ports, and dependency injection in discovery/monitoring | Replacement testing is not yet uniform for every external technology |
| 10 Failure Containment | Partial | Worker timeout, bounded retry, dead-letter lifecycle, alerts, transactional persistence, recovery contracts | Failure contracts are not documented uniformly at every capability boundary |
| 11 Critical Idempotency | Implemented | Canonical repository, worker, monitoring, persistence, and replay verifiers | New critical operations must continue to prove idempotency explicitly |
| 12 Data Durability | Implemented | PostgreSQL/MinIO authority, immutable ledgers, hashes, backup process, recovery and retraction/supersession contracts | Periodic restoration evidence needs stronger automation |
| 13 Restore-Tested Backup | Partial | Backup artifacts are checksummed and PostgreSQL dumps are structurally verified | No complete scheduled PostgreSQL, MinIO, knowledge, configuration, and graph restore drill |
| 14 Observability Contract | Implemented | Structured logs, correlation IDs, metrics, readiness, durable audit events, worker alerts | Capability-specific service-level signals can be expanded |
| 15 Security by Default | Implemented | Deny-by-default authentication, roles, secret templates, input validation, secure file boundaries, dependency audit | Ongoing threat review remains required for new surfaces |
| 16 Privacy/Data Separation | Partial | Storage contracts separate canonical, representation, operational, and backup data; logging avoids secrets | No complete repository-wide data classification, retention, deletion, and encryption matrix |
| 17 Boundary Contract Tests | Implemented | API, serialization, schema, repository, provider, database, snapshot, CLI verifier, and public namespace tests | Coverage must be checked for every newly introduced boundary |
| 18 Defect Regression Tests | Partial | Existing fixes commonly add regression coverage | No automated policy proves every defect commit contains an appropriate regression test |
| 19 Continuous Architecture Compliance | Implemented | Architecture Graph, law/compliance/review pipeline, ARC, and required CI gates | Law coverage can expand as capabilities grow |
| 20 No Orphan Implementation | Partial | FMA ownership, file registry, traceability graph, repository health, and architecture docs exist | Not every historical artifact has complete owner/capability/test/lifecycle traceability |
| 21 No Duplicate Authority | Implemented | Canonical PostgreSQL review/admission, source registry, schema registry, and graph provenance gates | Authority conflicts require continued review during extensions |
| 22 Rebuildable Derived Data | Implemented | Graphs, dashboards, indexes, reports, and representations retain source/hash provenance and rebuild paths | Invalidation policies should become more uniform and explicit |
| 23 Performance Budget | Not-yet-evidenced | Individual timeout and request limits exist | No capability-level latency, memory, storage, throughput, and cost budget baseline |
| 24 Simplicity Priority | Partial | Current architecture and vision discourage unnecessary infrastructure | No formal complexity-decision threshold or evidence template |
| 25 Bounded Change Scope | Partial | Sprint governance, focused commits, PR checks, and explicit unrelated-backlog practice exist | Enforcement depends substantially on review discipline |
| 26 Reviewability | Partial | Type hints, explicit domain models, focused modules, and PR workflow are common | No maintainability or complexity baseline across the repository |
| 27 Documentation Truth | Partial | Roadmaps, consolidation reports, completion baselines, and status corrections are evidence-bound | Historical documents still require periodic stale-status review |
| 28 Decision Memory | Partial | Governing vision, roadmap, consolidation, safety baseline, review events, and provenance exist | No general decision-record registry with supersession and rollback metadata |
| 29 Maintainer Handoff | Partial | Architecture, deployment, workflow, validation, and roadmap documents exist | Capability handoff coverage and known-failure documentation are uneven |
| 30 Human Approval | Implemented | Scientific review/admission, ARC review, FMA decisions, protected PR workflow, and explicit Codex authority boundary | New irreversible surfaces must preserve this invariant |

## Cross-cutting safety findings

1. No evidence was found that the new charter requires immediate source-code
   changes.
2. The current highest-value gap is restore testing, because verified backup
   creation is not equivalent to full restoration.
3. The largest compatibility-governance gap is the absence of a formal
   deprecation registry and removal lifecycle.
4. The largest reproducibility gap is the absence of a resolved transitive
   dependency lock or equivalent build attestation.
5. The largest planning gap is the absence of measurable capability-level
   performance budgets.
6. Existing FMA, P0 evidence-to-theory, branch protection, CI, persistence,
   and provenance controls already provide a strong foundation and must not be
   rebuilt under new names.

## Staged maintenance roadmap

Each phase is one separately approved, testable deliverable. Ordering reflects
risk reduction and dependency, not feature visibility.

### Phase 1 — Restore Evidence and Recovery Matrix

- inventory PostgreSQL, MinIO, knowledge, graph, configuration, and migration
  recovery paths;
- define isolated restore drills and immutable operational evidence;
- verify recovered hashes, schema, authority, and readiness; and
- never run a destructive restore against production without explicit human
  approval.

Primary rules: 04, 11, 12, 13, and 30.

### Phase 2 — Public Contract and Deprecation Registry

- inventory public constructors, enums, namespaces, APIs, events, schemas, and
  CLI/verifier contracts;
- define the canonical deprecation lifecycle and compatibility periods;
- add caller, replacement, milestone, migration-guide, and regression-test
  fields; and
- keep the registry advisory until architecture positioning and enforcement
  are separately approved.

Primary rules: 01, 02, 03, 17, 18, and 27.

### Phase 3 — Reproducible Build and Dependency Governance

- select a lock or build-attestation strategy compatible with Python 3.13 and
  the existing `pyproject.toml`;
- document dependency decision evidence and exit strategy;
- verify fresh-environment installation in CI; and
- preserve current pinned direct dependencies until migration is proven.

Primary rules: 07, 08, 09, and 24.

### Phase 4 — State, Cache, and Data Classification Registry

- identify configuration, environment variables, caches, temporary files,
  personal data, scientific data, publications, and operational artifacts;
- record owner, lifecycle, persistence, invalidation, retention, deletion,
  encryption, and audit requirements; and
- reconcile conflicts with existing storage contracts before enforcement.

Primary rules: 05, 15, 16, 21, and 22.

### Phase 5 — Failure and Observability Contract Coverage

- inventory exceptions, retry, timeout, idempotency, partial failure,
  rollback, recovery, dead-letter, audit, and correlation behavior;
- identify capability boundaries without explicit failure contracts; and
- add focused contracts without general refactoring.

Primary rules: 10, 11, 14, 17, and 19.

### Phase 6 — Decision Memory, Traceability, and Handoff

- define a general decision-record contract consistent with existing ARC,
  scientific review, FMA, and roadmap evidence;
- add supersession and rollback traceability;
- audit orphan artifacts and maintainer-handoff coverage; and
- avoid a second authority or parallel document registry.

Primary rules: 20, 21, 27, 28, and 29.

### Phase 7 — Performance and Maintainability Baseline

- define evidence-based budgets for critical capability latency, memory,
  storage, throughput, query cost, and external requests;
- record current measurements before optimization;
- establish reviewability and complexity indicators as advisory evidence; and
- prohibit optimization that breaks safety or architecture boundaries.

Primary rules: 23, 24, 25, and 26.

## Required workflow for every phase

Every phase begins with dependency verification and architecture positioning.
It then completes contract, domain-invariant, safety, data/migration,
security/privacy, failure/rollback, and test reviews before implementation.

Every phase closes using all 13 items in the Long-Term Engineering Charter.
No phase authorizes the next phase automatically.

## Initial recommendation

The first maintenance implementation should be **Phase 1 — Restore Evidence
and Recovery Matrix**. Scientific data durability has higher risk than
documentation convenience, performance optimization, or broad cleanup.

Before implementation, verify the existing backup constructor, backup ledger,
storage contracts, deployment boundaries, and whether restoration tooling
already exists outside the currently inspected canonical paths. Do not change
code until that dependency verification and architecture position are reported
and accepted.
