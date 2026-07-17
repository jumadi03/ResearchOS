# ResearchOS Long-Term Engineering Charter

## Status

- Document status: project-owner-accepted maintenance charter
- Formal ratification status: not defined by current repository governance
- Classification: long-term engineering and maintenance discipline
- Owner: ResearchOS project
- Authority: project owner
- Recorded: 2026-07-17
- Scope: all ResearchOS layers, subsystems, engines, capabilities, data,
  operations, documentation, and engineering work
- Related documents:
  `Documents/RESEARCHOS_VISION.md`,
  `Documents/RESPONSIBLE_EVOLUTION_VISION.md`,
  `Documents/ARCHITECTURE_GOVERNANCE.md`,
  `Documents/FILE_MANAGEMENT_SAFETY_BASELINE.md`, and
  `Documents/MAINTENANCE_BASELINE_AUDIT.md`

## Purpose and authority

This charter defines the long-term maintenance discipline for ResearchOS. It
complements the project charter, architecture laws, sprint workflow,
scientific governance, and implementation rules already in force.

This document does not replace canonical code, versioned architecture laws,
schema policies, scientific admission authority, or accepted subsystem
contracts. It does not authorize a repository-wide refactor. Existing
canonical code remains the Single Source of Truth for current constructors,
enums, public namespaces, lifecycle terms, persistence authority, and service
boundaries.

Every change must apply these rules proportionally to its scope. When a rule is
not yet enforced by code or automation, the limitation must remain explicit
and become input to the staged maintenance roadmap rather than being reported
as complete.

## Long-term engineering rules

### Rule-01 — Backward Compatibility by Default

New changes preserve existing contracts by default. A breaking change is
permitted only when technical necessity is demonstrated, impact is audited,
migration and rollback plans exist, every caller is identified, and the change
is explicitly approved.

Constructors, enums, return types, public namespaces, database schemas, event
payloads, and API contracts must never change silently.

### Rule-02 — Public Contract Before Internal Convenience

Internal convenience must not override public-contract stability. Every change
distinguishes the public contract, internal implementation, compatibility
adapter, and deprecated path. Internal refactoring is allowed only while public
behavior remains compatible.

### Rule-03 — Explicit Deprecation Lifecycle

No legacy component is removed immediately. The lifecycle is:

```text
ACTIVE
  -> DEPRECATED
    -> COMPATIBILITY PERIOD
      -> REMOVAL CANDIDATE
        -> REMOVED
```

Every deprecation records its reason, official replacement, removal date or
milestone, affected callers, migration guide, and regression tests for the
compatibility period.

### Rule-04 — Migration Before Mutation

When data structure, contract, or representation must change, migration
precedes mutation of the source of truth:

```text
Audit existing state
  -> Define target state
    -> Define migration
      -> Test migration
        -> Backup
          -> Apply change
            -> Verify
              -> Retain rollback path
```

Destructive mutation without a tested backup and rollback path is prohibited.

### Rule-05 — No Hidden State

All state that influences an outcome must be explicit and traceable. ResearchOS
must not depend on undocumented mutable globals, implicit singletons,
unregistered environment variables, caches without invalidation, unrecorded
local files, hidden execution ordering, or in-memory status as canonical
authority.

Important state has an owner, lifecycle, persistence policy, and provenance.

### Rule-06 — Deterministic Core, Controlled Nondeterminism

Kernel contracts, workflow structure, validation, admission gates, lifecycle,
and governance remain deterministic. Nondeterminism from AI, networks, time,
concurrency, and external sources is bounded, recorded, reproducible where
possible, and accompanied by seed or execution metadata when relevant.

Nondeterministic output cannot change canonical state without a validation
gate.

### Rule-07 — Reproducible Environment

Every ResearchOS version must be rebuildable from the repository. Dependency
locks or an equivalent controlled version strategy, runtime version, database
version, container configuration, environment template, migration version,
test commands, and bootstrap instructions must be available and maintained.

No production dependency may exist only as knowledge on a developer machine.

### Rule-08 — Dependency Discipline

Every new dependency requires justification covering existing alternatives,
maintenance, license, security history, release stability, transitive
dependencies, vendor lock-in, and exit strategy.

A dependency is not added merely to save a small amount of code. Dependency
versions are pinned or governed by an explicit version strategy.

### Rule-09 — Replaceability Requirement

Technology likely to change sits behind a contract or port, including AI
providers, database drivers, object storage, vector indexes, search providers,
message brokers, embedding models, document parsers, and authentication
providers.

Scientific domain code must not know vendor details. Every integration has a
replacement boundary.

### Rule-10 — Failure Containment

Failure in one capability must not corrupt another subsystem. Important
boundaries define exception contracts, retry, timeout, idempotency, partial
failure, rollback, dead-letter or recovery behavior, and audit events.

Exceptions must not be swallowed. Diagnostic cause and trace remain available.

### Rule-11 — Idempotency for Critical Operations

Critical operations are safe to repeat, especially ingestion, persistence,
migration, evidence admission, graph construction, publication, retry, event
processing, and backup restoration.

The same request or task must not accidentally create duplicate canonical
objects.

### Rule-12 — Data Durability Over Feature Speed

Scientific data takes priority over delivery speed. Changes affecting evidence,
provenance, artifacts, graphs, review events, publications, or scientific
decisions review durability, consistency, versioning, backup, restoration,
corruption detection, archival, supersession, and retraction.

No critical-data sprint closes without a clear restore or recovery path.

### Rule-13 — Backup Is Valid Only After Restore Test

A backup that has not been restored is not considered valid. PostgreSQL,
object storage, graph snapshots, artifact representations, configuration, and
migration rollback must be restored periodically. Restore results are retained
as operational evidence.

### Rule-14 — Observability Is Part of the Contract

An important component is incomplete when it cannot be observed. It provides,
as applicable, structured logs, correlation or execution identity, error
classification, metrics, health signals, audit events, provenance, and failure
reasons.

Observability never exposes sensitive data or secrets.

### Rule-15 — Security by Default

Every change follows least privilege, deny by default, no repository secrets,
input validation, output sanitization, authenticated administration, explicit
authorization, dependency vulnerability review, secure logging, and safe file
handling.

Security work is not deferred as cosmetic work.

### Rule-16 — Privacy and Scientific Data Separation

Scientific data, personal data, credentials, caches, temporary output, and
publication artifacts remain separated. Every data class has classification,
storage location, access policy, retention, deletion policy, encryption
requirement, and audit requirement.

Sensitive data must not enter logs, public fixtures, test snapshots, or commits.

### Rule-17 — Contract Tests at Every Boundary

Every public boundary has contract tests, including package namespaces, domain
model constructors, repository ports, provider adapters, APIs, events,
database mappings, serialization, snapshots, CLI tools, and verifiers.

Internal unit tests alone do not prove boundary stability.

### Rule-18 — Regression Test for Every Fixed Defect

Every fixed defect gains a regression test that fails before the correction
and passes afterward. A code-only patch does not complete a defect fix.

### Rule-19 — Architecture Compliance Is Continuous

Architecture review occurs for every change, not only at milestone completion.
Review covers layer ownership, dependency direction, public namespaces,
capability boundaries, canonical contracts, architecture laws, forbidden
imports, and bypass paths.

Passing functional tests cannot justify an architecture violation.

### Rule-20 — No Orphan Implementation

Every important file, class, service, API, table, migration, script, and
document has a subsystem, capability, contract, owner, test, governing
decision or document, and lifecycle.

Artifacts without traceability are repository-health issues.

### Rule-21 — No Duplicate Authority

One concept has one canonical authority. This includes evidence review state,
provider registry, configuration, lifecycle, routing decisions, artifact
identity, migration version, and public API.

Caches, snapshots, manifests, and derived models never replace canonical
authority. An authority conflict stops implementation until resolved.

### Rule-22 — Derived Data Must Be Rebuildable

Graphs, indexes, embeddings, caches, summaries, reports, and search projections
retain source references and content hash or version, can be rebuilt, are not
the only copy of canonical facts, and have an invalidation policy.

Important knowledge must not exist only in a vector index or cache.

### Rule-23 — Performance Budget Before Optimization

Optimization requires evidence. Important capabilities should define latency,
memory, storage, throughput, query-cost, and external-request budgets.

Premature optimization must not damage readability, testability, or
architecture boundaries.

### Rule-24 — Simplicity Has Priority

Use the simplest solution that satisfies proven contract, safety, and scaling
needs. Microservices, brokers, graph databases, separate vector databases,
distributed caches, orchestration platforms, and new abstraction layers
require actual need and operational evidence.

Complexity is a long-term cost.

### Rule-25 — Change Scope Must Remain Bounded

One sprint must not become general cleanup. Every change bounds its objective,
files, contracts, dependencies, tests, migration, and risk.

Unrelated findings become separate backlog items.

### Rule-26 — Reviewability Requirement

Code favors explicit names, small focused functions, readable control flow,
type hints, meaningful exceptions, comments explaining reasons, limited
metaprogramming, and no premature abstraction.

Code that is clever but difficult to inspect is a maintenance risk.

### Rule-27 — Documentation Follows Implementation Truth

Documentation changes with behavior and contracts, but never claims unavailable
implementation. Status terms such as planned, draft, partial, implemented,
verified, deprecated, and archived remain evidence-based.

Terms such as complete, canonical, ratified, and production-ready require
appropriate evidence and repository governance.

### Rule-28 — Decision Memory Is Mandatory

Breaking changes, architecture corrections, new canonical contracts, database
migrations, provider strategy, security or scientific policy, compatibility
removal, and major dependencies have a permanent decision record.

The record includes context, alternatives, decision, rationale, consequences,
risks, rollback, reviewer, and superseded decision.

### Rule-29 — Maintainer Handoff Readiness

Important capabilities can be understood by a new maintainer without relying
on the original author. They document purpose, architecture position, public
contract, execution flow, dependencies, tests, failure modes, operations, and
known limitations.

A component understood by only one person is not healthy.

### Rule-30 — Human Approval for Irreversible Changes

Codex and other automation must not perform irreversible actions without
explicit human approval. This includes destructive migration, deletion of
canonical data, removal of compatibility, history rewriting, force-push,
production deployment, secret rotation, changes to scientific admission
policy or authority rules, and modification of governing documents.

Automation may audit, simulate, prepare patches, and recommend. Irreversible
decisions remain under human authority.

## Required sprint closure

A sprint is complete only when its report covers:

1. dependency verification;
2. architecture position;
3. contract impact;
4. data and migration impact;
5. security and privacy impact;
6. failure and rollback behavior;
7. tests and commands executed;
8. architecture compliance;
9. documentation impact;
10. Git status;
11. known limitations;
12. follow-up backlog; and
13. confirmation that no unrelated changes were introduced.

Items that do not apply must be marked `not applicable` with a reason rather
than omitted.

## Long-term definition of a healthy ResearchOS

ResearchOS is healthy when it can be rebuilt, retested, restored from backup,
switch providers, migrate data, explain every important decision, reject
invalid state, detect architecture violations, and be understood by a new
maintainer.

It must evolve without casually breaking old contracts and must retain humans
as the final authority for scientific decisions and irreversible changes.

## Application rule

This charter is applied incrementally. It does not authorize changing the
entire repository at once. The current implementation status is recorded in
[`MAINTENANCE_BASELINE_AUDIT.md`](MAINTENANCE_BASELINE_AUDIT.md); that audit is
the basis for bounded maintenance increments.

