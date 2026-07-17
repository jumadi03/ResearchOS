# File Management Architecture Completion and Safety Baseline

- Baseline date: 2026-07-17
- Baseline commit: `14b38be46ec55af49a74dde023b1b318a8b9ebcc`
- Architecture position: Architecture Engine / Repository Management
- Scope: FMA-001 through FMA-008
- Acceptance status: completed and verified
- Production repository mutation: prohibited

## Purpose

This document records the final acceptance evidence for the File Management
Architecture defined in
[`FILE_MANAGEMENT_ARCHITECTURE.md`](FILE_MANAGEMENT_ARCHITECTURE.md). It is an
audit baseline, not a new runtime capability and not an authorization to move,
rename, delete, or mass-register files in the ResearchOS repository.

Existing canonical code remains the Single Source of Truth. This baseline
records the implementation position, safety invariants, compatibility,
verification evidence, activation boundaries, and residual operational risks
observed at the baseline commit.

## Final acceptance decision

FMA-001 through FMA-008 are accepted as a complete, ordered architecture
capability set at the baseline commit.

Acceptance means:

- every planned FMA capability has a canonical implementation boundary;
- immutable outputs are content-addressed and provenance-bearing where the
  capability produces durable audit evidence;
- report-only, decision, execution, recovery, and closure responsibilities
  remain explicit and separate;
- unsafe or stale inputs fail closed at their service boundary;
- no parallel Architecture Graph or compliance engine was introduced;
- all required local regression and architecture tests pass; and
- the six GitHub Architecture Quality Gate jobs pass for the baseline commit.

Acceptance does **not** mean:

- repository evolution is activated against the ResearchOS source tree;
- a report-only finding is a compliance verdict;
- a dashboard projection is canonical evidence;
- a dry run or human-approved plan is an execution authorization; or
- lifecycle closure authorizes production activation.

## Implementation traceability

| Deliverable | Canonical capability | Implementation commits | Acceptance |
| --- | --- | --- | --- |
| FMA-001 | Deterministic, revision-bound repository classification | `a018501` | Accepted |
| FMA-002 | Immutable repository policy registry | `d628263` | Accepted |
| FMA-003 | Deterministic file identity and continuity registry | `e1dc0db` | Accepted |
| FMA-004 | Report-only placement and naming verification | `7e4aec2` | Accepted |
| FMA-005 | Repository traceability in the existing Architecture Graph | `46e846d` | Accepted |
| FMA-006 | Deterministic, report-only repository health assessment | `d4066c8` | Accepted |
| FMA-007 | Dashboard projection, immutable publication, and bilingual administration view | `778bd1c`, `c03947c`, `166e54e` | Accepted |
| FMA-008 | Plan, preflight, dry run, isolated execution, post-verification, recovery, post-recovery revalidation, and attributable lifecycle closure | `da6e3ac`, `a035f2f`, `ceb7c49`, `9b7dce7`, `e6f5241`, `d2f0990`, `1ad6fdc`, `dea9289`, `14b38be` | Accepted |

The governing roadmap was established in `f4c9570` and normalized in
`5a81753`.

## Dependency and architecture verification

The accepted position is:

- **Layer:** architecture and governance;
- **Subsystem:** Repository Management;
- **Engine:** existing Architecture Engine;
- **Capability:** classification, policy, registry, verification,
  traceability, health, dashboard projection, and controlled evolution.

FMA extends existing schema compatibility, Architecture Graph, ARC,
transactional persistence, and bilingual interface contracts. It does not
create a second graph, a second compliance authority, a new database lifecycle
enum, or an alternative evidence authority.

## Domain invariants

The following invariants are mandatory:

1. Canonical file identity is stable across an attributable path transition.
2. Registry, graph, and evaluation artifacts must identify their source
   revision and canonical upstream hashes.
3. Unknown identities, stale paths or hashes, conflicting policies, occupied
   targets, incomplete rollback definitions, and broken provenance fail
   closed.
4. Classification, verification, health, and dashboard results do not become
   compliance decisions by implication.
5. A proposed or approved migration plan is not executable.
6. Preflight and dry-run artifacts do not authorize execution.
7. Isolated execution must be root-confined, reject symlink escape and
   overwrite, verify content hashes, and preserve an exact rollback sequence.
8. Execution success alone cannot establish canonical migration success.
9. Recovery success alone cannot close a migration lifecycle.
10. Lifecycle closure requires either a complete verified migration chain or a
    complete recovered-and-reverified chain plus attributable human identity,
    rationale, and a timezone-bearing decision timestamp.
11. Lifecycle closure neither mutates the repository nor authorizes production
    activation.

## Defense-in-depth and bypass audit

| Boundary | Fail-closed behavior |
| --- | --- |
| Policy registry | Rejects conflicting ownership, placement, naming, lifecycle, and exception contracts |
| File registry | Rejects invalid identity, hash, classification, ownership, and continuity state |
| Placement verifier | Emits evidence-bearing report-only outcomes; cannot declare compliance |
| Traceability graph | Reuses the canonical Architecture Graph and binds repository provenance |
| Health engine | Distinguishes observed findings, advisory results, and not-evaluated state |
| Dashboard | Publishes immutable projections; cannot substitute for canonical artifacts |
| Evolution planner | Rejects stale or unknown sources, occupied targets, duplicate targets, incomplete rollback, and unattributed decisions |
| Preflight | Revalidates current registry and graph; stale or unsafe state is not ready |
| Dry run | Requires matching ready preflight; never mutates or authorizes |
| Isolated executor | Revalidates the full contract at the mutation boundary and confines all paths to an isolated root |
| Post-verification | Requires advanced canonical revision, exact continuity, and current graph provenance |
| Recovery governance | Separates recovery decision from recovery execution |
| Recovery executor | Accepts only an eligible recovery chain and records partial or manual-recovery states explicitly |
| Post-recovery verifier | Requires restored identity, path, hash, continuity, revision, and graph provenance |
| Closure auditor | Revalidates the complete final chain and human attribution even when invoked directly |

No supported direct service invocation bypasses the FMA-008 admission,
execution, recovery, revalidation, or closure gates.

## Compatibility review

- Existing repository lifecycle terminology is unchanged.
- Existing schema policies remain readable at their canonical versions.
- No database migration is introduced by FMA.
- No existing Kernel, evidence lifecycle, knowledge graph, or Theory Builder
  contract is renamed.
- The bilingual interface contract remains Indonesian/source-language aware.
- Existing tests remain compatible at the baseline commit.

## Verification evidence

### Local acceptance

At the closure implementation commit:

- focused repository evolution suite: **47 passed, 1 skipped**;
- complete architecture suite: **191 passed, 2 skipped**;
- schema, ARC, and persistence governance suite: **18 passed**;
- full regression suite: **345 passed, 2 skipped**;
- architecture, observability, and architecture-router coverage:
  **94.32%** against a required **90%**;
- dependency consistency: passed; and
- Git diff integrity: passed.

The skipped tests are platform-dependent symlink tests. Four warnings in the
full suite are existing dependency and datetime deprecations; they do not
weaken an FMA safety gate.

### GitHub acceptance

[Architecture Quality Gates run
29574921410](https://github.com/jumadi03/ResearchOS/actions/runs/29574921410)
completed successfully for the baseline commit. All six jobs passed:

1. Full regression and architecture coverage;
2. Knowledge and product regression;
3. Container and deployment contracts;
4. PostgreSQL and MinIO integration;
5. Schema, ARC, and persistence gates; and
6. Dependency security.

## Activation boundary

The following capabilities are accepted for normal use:

- repository scanning and classification;
- policy, registry, verification, traceability, and health evaluation;
- immutable dashboard publication and bilingual dashboard reading; and
- creation and audit of non-production evolution artifacts.

The following remains prohibited:

- wiring the isolated evolution or recovery executor to an API, worker,
  deployment volume, or the ResearchOS source root;
- treating lifecycle closure as production activation;
- automated mass migration;
- deletion or overwrite as an implicit migration strategy; and
- weakening root confinement, no-overwrite, hash, provenance, or human
  attribution checks.

Production activation requires a separate dependency verification,
architecture position, threat model, authorization boundary, operational
rollback plan, and independently accepted deliverable.

## Residual risks and follow-up

1. Branch administration currently permits a privileged direct push while
   required checks are still expected. The baseline is accepted because the
   post-push run completed successfully, but pull-request enforcement is a
   recommended operational hardening.
2. Existing Starlette/httpx and naive-UTC deprecation warnings should be
   removed in a separate compatibility sprint.
3. Symlink tests may skip on hosts that do not grant symlink creation
   privileges; Linux CI remains the authoritative cross-platform gate.
4. FMA-008 executors have deliberately not been validated for production
   repository activation because that capability is outside the accepted
   scope.

These items do not represent a bypass in the accepted FMA architecture. They
remain explicit constraints for future work.

## Change control

Any future change to FMA must repeat:

1. Dependency Verification;
2. Architecture Position;
3. Contract Review;
4. Domain Invariant Review;
5. Safety Review;
6. Unit, Integration, Architecture, and Compliance Test Plan; and
7. an explicit Definition of Done.

This baseline may be superseded only by a newer attributable baseline that
identifies its source commit, changed invariants, compatibility impact, test
evidence, and activation decision.
