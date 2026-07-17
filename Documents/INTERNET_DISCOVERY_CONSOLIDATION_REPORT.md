# Internet Discovery Consolidation Report

## Review status

- Review: SCAN-001O Consolidation Review
- Status: project-owner-accepted and consolidation-verified
- Acceptance recorded: 2026-07-17
- Recorded: 2026-07-17
- Owner: Scientific Knowledge Subsystem
- Architectural position: Discovery Engine / Consolidation Review capability
- Governing roadmap: `Documents/INTERNET_DISCOVERY_ROADMAP.md`

This report records the path-verified implementation position of P0 and
SCAN-001A through SCAN-001O. It is an implementation and compliance record,
not a claim of formal ratification or scientific validation.

## Review method

The review verified existing constructors, enums, lifecycle states, service
boundaries, dependency direction, persistence authority, API contracts, tests,
and executable compliance checks before changing code. Existing canonical code
remained the single source of truth. SCAN-001O only extends the existing
monitoring capability and closes gaps found by the consolidation review.

## Capability traceability

| Deliverable | Canonical implementation | Persistence or verifier | Consolidation result |
| --- | --- | --- | --- |
| P0 | `app/knowledge/evidence_admission.py`, graph and theory guards | PostgreSQL evidence review/admission ledgers and canonical evidence/graph verifiers | Accepted-only knowledge and theory boundary remains defense in depth |
| SCAN-001A | discovery contract models | discovery snapshots and discovery regression | Explicit scope, limits, licensing, and review policy |
| SCAN-001B | `discovery/source_registry.py` | registry verification in discovery tests | Canonical source authority and access policy |
| SCAN-001C | `discovery/query_planner.py` | deterministic query-plan validation | Contract-bound, source-specific planning |
| SCAN-001D | discovery engine and provider enumeration | discovery run snapshots | Provenance-bound candidate inventory |
| SCAN-001E | controlled acquisition contracts and adapters | raw request/response records | Preferred structured acquisition order and fail-closed controls |
| SCAN-001F | raw capture and content-addressed storage | MinIO representation verifier | Immutable bytes, hashes, media metadata, and storage references |
| SCAN-001G | source inspection models and services | inspection regression | Factual inspection without scientific acceptance |
| SCAN-001H | identity resolution and canonical repository | identity-resolution ledger and repository verifier | DOI/provider identity decisions are attributable and reproducible |
| SCAN-001I | screening models and service | screening decision ledger and tests | Explicit inclusion/exclusion decisions and reasons |
| SCAN-001J | evidence extraction pipeline | extraction manifests and snapshots | Source-located provisional evidence only |
| SCAN-001K | evidence review lifecycle | immutable review events | Human decision is required before admission |
| SCAN-001L | knowledge intake and graph builder | canonical evidence and graph verifiers | Only currently accepted, fully provenanced evidence enters knowledge |
| SCAN-001M | citation traversal | citation candidate inventory and verifier coverage | Reproducible discovery-only snowballing |
| SCAN-001N | monitoring domain, worker, and repository | monitoring ledgers and worker regression | Deterministic discovery-only change detection |
| SCAN-001O | lifecycle/read APIs and dependency inversion | `deploy/verify/continuous_monitoring.py` and architecture checks | End-to-end boundary is executable and auditable |

Paths in the table are relative to `AI-Gateway/` unless they start with
`deploy/` or `Documents/`.

## Consolidation changes

The review identified and closed four concrete gaps:

1. The monitoring executor previously constructed PostgreSQL and provider
   adapters. It now receives repository and provider dependencies, with the
   worker as the composition root.
2. Paused watches had no controlled transition contract. Pause and resume now
   require a valid lifecycle transition, owner authority, actor identity,
   rationale, time, and an immutable transition event.
3. Monitoring runs and detected changes lacked read APIs. Authenticated read
   models now expose runs and discovery-only changes, including acknowledgement
   state.
4. CI lacked a PostgreSQL monitoring proof. The new verifier exercises
   baseline persistence, lifecycle changes, comparison, idempotent persistence,
   reads, acknowledgement, and non-promotion into evidence or knowledge.

The review also corrected an existing PostgreSQL parameter-typing ambiguity in
scientific document upsert so the integration path is executable on the
canonical PostgreSQL version.

## Safety proof

- A monitoring change is labeled `discovery_only`; it is not evidence.
- Monitoring persistence writes no evidence object and no knowledge edge.
- Pause/resume is limited to `active -> paused` and `paused -> active`.
- Only the recorded watch owner may change lifecycle state.
- Every lifecycle decision records actor, rationale, occurrence time, and
  immutable transition identity.
- A paused or expired watch cannot run or persist a monitoring result.
- Replaying an identical monitoring result is idempotent; conflicting content
  fails closed.
- Provider failure does not imply source unavailability.
- Every candidate still passes screening, extraction, human review, P0
  admission, graph, and theory guards.

## Compatibility

- Existing evidence states remain `PROVISIONAL`, `ACCEPTED`, and `REJECTED`.
- Existing PostgreSQL review terms remain `pending`, `accepted`, and
  `rejected`.
- No evidence-state synonym or new promotion path was introduced.
- Existing monitoring status terms remain `active`, `paused`, and `expired`.
- Schema version advances from 27 to 28 through an additive migration.

## Residual risks and deliberate limits

- The monitoring read endpoints currently return complete watch-scoped result
  sets; pagination is a future operational hardening need for large histories.
- Source availability is not inferred from disappearance. An affirmative
  provider-level unavailability contract remains future work.
- Provider breadth is constrained by the canonical source registry and
  implemented adapters; adding sources requires the normal contract and
  compliance process.
- This review proves software invariants and provenance. It does not certify
  the truth, quality, or scientific significance of discovered publications.

## Definition of Done evidence

Final acceptance requires:

- focused monitoring, API, worker, and architecture tests pass;
- full regression and architecture compliance pass;
- schema version, migration, canonical repository, storage, evidence, graph,
  and MinIO representation verifiers pass;
- continuous-monitoring PostgreSQL verifier prints
  `continuous-monitoring=passed`;
- Compose configuration and dependency consistency pass; and
- `git diff --check` passes.

Exact final counts and commit identity are reported in the sprint completion
record after all checks finish. Project-owner acceptance was subsequently
recorded after the implementation, consolidation evidence, and safety
boundaries were reviewed.

## Validation record

Validation completed on 2026-07-17:

- focused monitoring, API, worker, and architecture regression:
  **56 passed**;
- full ResearchOS regression: **238 passed**;
- architecture compliance: **84 passed**;
- dependency consistency and Python compilation: passed;
- Compose configuration and schema version 28 healthcheck: passed;
- canonical repository, representation, source inspection, screening,
  evidence, and graph verifiers: passed on a fresh isolated stack;
- continuous-monitoring verifier: `continuous-monitoring=passed`;
- resilient-worker verifier: `resilient-worker=passed`;
- storage compliance: passed with **45 contracts** and **14 representations**
  verified; and
- `git diff --check`: passed.

Four regression warnings are pre-existing framework and UTC datetime
deprecations. They do not weaken monitoring lifecycle, provenance, admission,
graph, or theory safety invariants.
