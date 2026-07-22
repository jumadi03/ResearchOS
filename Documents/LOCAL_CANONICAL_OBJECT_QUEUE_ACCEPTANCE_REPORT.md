# Canonical Object Browser and Work Queue Acceptance

Date: 2026-07-19  
Target: `http://localhost:3003/`  
Migration stage: UI canonical migration sequence, stage 2

## Decision

**ACCEPTED for local read-only operation.**

The canonical UI now exposes the project object browser and project work queue
using authenticated ResearchOS APIs. Scientific decisions and lifecycle
mutations remain in the legacy operational workspace until their governed forms,
CSRF handling, confirmations, and audit acceptance are migrated.

## Implemented scope

- Active-project selection using the canonical project list.
- Object listing in pages of 30 with backend cursor pagination.
- Debounced server-side search by title or stable key.
- Object-type filter for documents, evidence, and artifacts.
- Explicit loading, empty, and error states.
- Object inspector with canonical identity, lifecycle, classification, version,
  and backend-authorized action names.
- Read-only work-queue metrics and bounded previews for evidence review,
  lifecycle transitions, and impact review.
- Handoff links to the audited operational workspace with project and object
  context preserved.

## Browser verification

Interactive verification against the local production data passed:

- ResearchOS project selected automatically.
- First page loaded 30 objects from a total project count of 320.
- Search for `Gap healthcheck` narrowed the server result correctly.
- Selecting the matching artifact loaded its stable identity and lifecycle
  detail in the inspector.
- The empty-result state appeared for a valid filter/query combination with no
  matches.
- Work queue loaded 5 pending evidence reviews and 52 pending transitions.
- Audit handoff links retained `project=researchos-default` and, where
  applicable, the selected object identifier.

## Automated verification

- Production UI build: passed.
- Site tests: **5 passed, 0 failed**.
- Contract coverage verifies object-list, work-queue, cursor, authorization
  capability display, fail-closed proxy behavior, and the explicit audited
  mutation boundary.

## Trust boundary

The UI does not infer permissions from account roles. It displays only
`available_actions` and boolean queue capabilities returned by the backend.
No mutation button was added in this stage. This prevents an incomplete UI from
bypassing reviewer rationale, confirmation, CSRF, provenance, or audit-event
requirements.

## Next gate

Superseded on 2026-07-19 by
`LOCAL_CANONICAL_DECISION_ACCEPTANCE_REPORT.md`: governed evidence review and
artifact lifecycle transition forms subsequently passed local acceptance.

At the time of this report, the canonical UI still needed the following items;
they are now completed by the superseding acceptance:

1. governed evidence-review and lifecycle-transition forms;
2. success, validation-failure, unauthorized, and stale-state browser tests;
3. persisted-decision verification after refresh;
4. rollback acceptance to the legacy workspace.
