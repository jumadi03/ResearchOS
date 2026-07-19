# ResearchOS Canonical UI Migration

Status: Accepted

## Decision

ResearchOS will migrate incrementally from the FastAPI-served browser workspace
to `site/`. The existing `/workspace` remains the canonical operational UI
until the new UI reaches capability and trust-boundary parity. The `site/`
application is the canonical target UI.

## Authority boundary

FastAPI remains the sole authority for identity, authorization, provenance,
scientific decisions, architecture compliance, audit records, and persistence.
The UI may present data and submit user intent, but it must not infer or promote
scientific or governance status locally.

The new UI must:

- use the ResearchOS session and CSRF contracts;
- load research data only from ResearchOS APIs;
- render unavailable and unauthenticated states without fabricated data;
- preserve role-based navigation and action availability;
- keep `/workspace` available as the operational fallback during migration.

## Migration sequence

1. Session-aware application shell and canonical project list.
2. Object browser and project work queue.
3. Discovery and source inspection.
4. Evidence screening and human review.
5. Theory, graph, validation, and publication.
6. Administration, audit, recovery, and observability.

## Current progress

- Stage 1: accepted locally (session-aware shell and canonical project list).
- Stage 2: accepted locally. This includes the object browser, search, type
  filter, detail inspector, cursor pagination, project work queue, governed
  evidence-review form, and artifact lifecycle-transition form.
- Stage 2 reviewer decisions and lifecycle transitions passed fail-closed,
  role-boundary, CSRF, source-hash, audit-event, and refresh-persistence
  acceptance. Publication release remains separately publisher-gated.
- Stage 3: accepted locally through source screening. Governed discovery,
  provider provenance, metadata enrichment, provenance-bound acquisition,
  checksum verification, source inspection, and contract screening passed.
- Stage 4: accepted locally end to end. Evidence
  extraction is available only after eligible screening, produces provisional
  objects, and preserves human-review authority. Equivalent content processed
  with the same parser reuses its canonical extraction manifest; browser
  acceptance confirmed that repeated extraction did not increase the object or
  review-queue totals. The reviewer form exposes source coordinates and bound
  hashes, reviewer decisions persist after refresh, accidental decisions can
  be corrected through append-only events, and rejected evidence is separated
  from active work while remaining available as an audit archive.
- One duplicate five-object batch created while diagnosing pre-fix behavior
  remains disclosed in the local acceptance database. It was not silently
  removed or rewritten.

Each migrated capability must have contract tests and must preserve the backend
authorization decision. A module can replace its legacy equivalent only after
its success, failure, unauthenticated, unauthorized, and empty states have been
verified.

## Cutover gate

`site/` becomes the operational canonical UI only when:

- all displayed research data comes from the canonical backend;
- login, logout, session refresh, CSRF, and primary roles are verified;
- the discovery-to-publication workflow is complete;
- accessibility, browser, and backend contract tests pass;
- rollback to the legacy workspace has been exercised.

After cutover, the legacy workspace remains frozen for one stabilization
release before removal.
