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

### Phase 1A implementation traceability

Phase 1A establishes the backup-set and restore-evidence foundation. New backup
runs publish a deterministic portable manifest and store its hash in
PostgreSQL. Restore verification is modeled as a separate immutable ledger,
bound to the exact backup ID and set hash and restricted to isolated targets.
The administration API and interface no longer equate archive integrity with a
successful restore. Compatibility is additive: the historical `ready` response
remains but is explicitly marked as a deprecated backup-integrity alias.

This does **not** complete Rule 13. No restore executor or scheduled full drill
is introduced here, and architecture/configuration components are not yet
included in the produced set. Consequently `recovery_ready` remains fail-closed
until a later accepted increment performs and records a matching isolated
restore.

### Phase 1B implementation traceability

Phase 1B defines `researchos-recovery-coverage-v1` as the versioned recovery
inventory for PostgreSQL, MinIO, knowledge, architecture, configuration, and
migration. Its verifier is deterministic and report-only: it binds the matrix
and backup manifest hashes, verifies current artifacts, requires explicitly
isolated future targets, rejects unsafe paths and unexpected components, and
prohibits configuration secret values.

The accepted status vocabulary is `covered`, `partial`, and `missing`; the
aggregate is `COMPLETE` or `INCOMPLETE`. The current matrix truthfully reports
architecture and configuration as missing and migration as partial. Therefore
Phase 1B does not complete Rule 13, write restore evidence, execute a restore,
or authorize mutation of an active target. Its output determines the bounded
coverage work required before an isolated restore drill can be implemented.

### Phase 1C implementation traceability

Phase 1C closes the three backup-coverage gaps identified by Phase 1B.
Architecture, allowlisted non-secret configuration, and versioned migration
sources join PostgreSQL, MinIO, and knowledge in the portable manifest. Stable
filesystem snapshots reject symbolic links, compare tree manifests before and
after copying, retry no more than three times, and retain the accepted manifest
inside each archive.

Configuration mounts are explicit and exclude the active `stack.env`, local
access credentials, passwords, and tokens. Migration coverage contains the
runner and complete ordered SQL set; the PostgreSQL dump retains the matching
`schema_migrations` ledger. An empty architecture volume is represented by an
explicit empty tree manifest rather than being inferred as missing.

All six components may now be `covered` and the aggregate matrix may be
`COMPLETE`. This is readiness for an isolated restore drill only. Phase 1C does
not execute a restore, write `backup_restore_verifications`, mutate an active
target, or complete Rule 13.

### Phase 1D implementation traceability

Phase 1D adds a manual isolated restore-drill executor without connecting it to
the API, worker, scheduler, active stack, or immutable restore ledger. A
standalone Compose project has only an internal network, read-only backup input,
tmpfs PostgreSQL and MinIO targets, and fixed executor-owned database and bucket
identities. Active volume mounts, active hostnames, `stack.env`, and
operator-selected target identifiers are absent.

The executor revalidates coverage and manifest hashes before target mutation.
It rejects unsafe archive members, verifies four filesystem tree manifests and
the configuration allowlist, restores PostgreSQL and reconciles the complete
schema migration ledger, restores MinIO and verifies object sizes and content
hashes, then removes the temporary database and bucket. Blocked, failed, and
verified outcomes remain explicit and every report is attributable and
content-hashed.

Phase 1D proves that a complete backup set can be restored in isolation, but it
does not yet satisfy the operational recovery projection. The report explicitly
states `ledger_written: false`; admission to the append-only
`backup_restore_verifications` ledger requires a separate contract review and
accepted increment.

### Phase 1E implementation traceability

Phase 1E closes the restore-evidence admission gap without coupling the
isolated drill to the active application. The drill signs a canonical report
with a local Ed25519 private key. A separate, manually invoked admission
service receives only the report, public trust registry, and database
connection; it verifies cryptographic and semantic integrity before calling
the schema 30 admission function.

Defense in depth remains active after admission. PostgreSQL rejects incomplete
verified rows and preserves append-only evidence. The recovery projection
revalidates the stored report and signature against the current trust registry,
so direct insertion, tampering, key revocation, or stale admission state cannot
produce operational readiness. Admission is idempotent by content hash and no
API, UI, worker, scheduler, private-key mount, or active-target path is added.

### Phase 1F-A implementation traceability

Phase 1F-A prevents indefinitely old restore evidence from sustaining an
operational readiness claim. The live recovery projection now separates
cryptographic validity (`restore_verified`) from bounded temporal validity
(`restore_fresh`). `recovery_ready` requires both, along with the matching
portable backup-set integrity proof.

The maximum age and future clock-skew allowance are positive, server-owned
configuration. Exact-boundary evidence is accepted; stale evidence and
timestamps beyond the allowed future skew fail closed with explicit reasons.
The immutable evidence remains unchanged, and this increment introduces no
scheduler, worker job, orchestration service, private-key exposure, database
migration, or direct admission path.

### Phase 1F-B implementation traceability

Phase 1F-B adds the coordination foundation required before periodic execution.
Schema 31 defines one operational restore-drill run lease and a separate
append-only lifecycle-event ledger. PostgreSQL, rather than a client path,
selects the latest eligible backup and returns its safe manifest filename.

Only one run may be active. Lease identity, owner, backup binding, and expiry
are immutable. Completion requires a matching canonical Phase 1E verification
ID and report content hash. Wrong tokens, concurrent acquisition, mismatched
evidence, and expired completion fail closed with explicit reasons.

The coordinator is DB-only and has no private key, backup/report/trust mounts,
Docker socket, API route, or worker integration. This increment does not add a
scheduler or execute the drill automatically.

### Phase 1F-C implementation traceability

Phase 1F-C adds a manually invoked host controller that composes the accepted
Phase 1F-B lease, Phase 1D isolated execution, Phase 1E signed admission, and
canonical completion contracts. The controller never accepts a backup path,
restore target, database URL, private-key path, report path, or verification
identity from the operator. PostgreSQL selects the backup; the drill and
admission services retain their existing isolated mounts and authorities.

Every post-acquisition failure attempts an explicit canonical lease failure,
and isolated Compose cleanup is attempted even when execution fails. Admission
receipts provide the exact report content hash and verification ID used for
completion. The controller is host-only, uses fixed argument arrays without a
shell, and adds no API, UI, worker, scheduler, or container Docker socket.

### Phase 1F-D implementation traceability

Phase 1F-D adds Schema 32 canonical schedule governance without adding a
scheduler daemon. The single schedule starts paused, has a server-owned
one-to-thirty-one-day cadence bound, and retains its policy hash, revision,
next due time, pending slot, and append-only actor-attributed events.

Only PostgreSQL decides whether a host request is paused, not due, already
running, or eligible to acquire a lease. Repeated triggers cannot create a
second run or obtain the active lease token. Completion, failure, and expiry
advance the schedule from its canonical slot rather than from client time.
Configuration, pause, and resume require an actor and rationale and are blocked
while a slot is active.

The Phase 1F-C controller adds only a `--scheduled` request mode. It remains
host-only, while the API and scientific worker receive no Docker authority,
signing material, schedule mutation path, or restore target access.

### Phase 1F-E implementation traceability

Phase 1F-E defines the Windows host-trigger contract without activating it.
The fixed Task Scheduler definition invokes the accepted Phase 1F-C controller
in scheduled mode every hour, while PostgreSQL Schema 32 remains the only due
authority. The task uses the current interactive Windows identity, limited
run level, a fixed three-hour execution limit, and an ignore-new
multiple-instance policy.

Planning and status are read-only. Installation verifies the canonical
controller, ResearchOS virtual environment, and Docker command, rejects an
existing task rather than silently replacing it, and registers the task
disabled. Removal requires an explicit confirmation switch and never deletes
schedule state, audit events, reports, or restore evidence. No password,
database URL, target, manifest, report, key path, or lease token enters the
task definition.

This increment provides an installable contract only. Enabling the Windows
task, activating the canonical database schedule, and producing the first
periodic restore proof require a separately approved operational step.

### Phase 2A implementation traceability

Phase 2A introduces an advisory, content-addressed Public Contract Registry in
the existing Architecture Governance subsystem. Its initial inventory records
five verified surfaces spanning the Kernel namespace, health/readiness HTTP
contract, database migration ledger, scheduled restore-controller CLI, and the
deprecated recovery `ready` compatibility alias.

The registry uses the canonical lifecycle `active`, `deprecated`,
`compatibility_period`, `removal_candidate`, and `removed`. Every non-active
entry must identify its official replacement, milestone, migration guide,
affected callers, and regression tests. Duplicate identities or public
surfaces, incomplete deprecation records, tampering, and unknown schema
versions fail validation.

This phase is deliberately advisory. It does not remove a contract, mutate a
caller, change a runtime API, enforce a removal decision, or create a second
schema authority. Expansion of the inventory and any enforcement require
separately approved deliverables.
