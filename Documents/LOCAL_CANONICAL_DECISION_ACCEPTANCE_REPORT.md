# Canonical Reviewer Decision and Lifecycle Acceptance

Date: 2026-07-19  
Target UI: `http://localhost:3003/`  
Backend: `http://127.0.0.1:8080`

## Decision

**ACCEPTED for local reviewer operation.**

The canonical UI can now record governed evidence reviews and artifact
lifecycle transitions using the backend session, CSRF, role, provenance, and
audit contracts.

## Implemented controls

### Evidence review

- The action is displayed only when `can_review` is explicitly `true`.
- Decision, rationale, confidence, epistemic classification, citation fidelity,
  context preservation, and relevance are submitted explicitly.
- Statement and extraction-manifest SHA-256 hashes come from the canonical work
  queue and cannot be edited in the form.
- Human confirmation is mandatory.
- The authenticated backend session determines reviewer identity.
- CSRF is supplied from the verified session.

### Artifact lifecycle

- The action is displayed only for a role allowed by the backend.
- The destination state comes from `next_status`; it is not an editable form
  value.
- Reviewer confirmation and rationale are mandatory.
- Publication remains separately gated to the publisher role.

## Defect found and corrected

The first lifecycle acceptance attempt failed closed with:

`Unknown canonical artifact: <canonical-object-uuid>`

The PostgreSQL work queue exposed the canonical object UUID, while the
lifecycle endpoint resolves the domain artifact ID represented by the
`artifact:` stable key.

Corrections:

- `postgres_read_model.py` now strips the `artifact:` prefix and exposes the
  domain artifact ID in pending transitions.
- `repository_service.py` now builds evidence-review and artifact-transition
  action URLs from the domain portion of the stable key, while retaining a
  compatibility fallback for test/read models without stable keys.
- A regression assertion protects the PostgreSQL projection contract.

No lifecycle mutation occurred during the failed attempt.

## Browser acceptance

### Role boundary

- Admin session: mutation buttons were absent.
- Reviewer session: evidence-review and non-publication lifecycle actions were
  present.

### Evidence review

- The dedicated acceptance record
  `This object remains pending for admission rejection testing.` was reviewed.
- Submission without confirmation was rejected by the UI.
- The record was rejected with explicit rationale and assessments.
- Pending evidence reviews decreased from 5 to 4.
- After a full page refresh the record remained absent from the pending queue.

### Lifecycle transition

- Submission without confirmation was rejected by the UI.
- A queued scientific theory bundle transitioned from `draft` to `review`.
- The refreshed queue exposed its next backend transition as
  `review` to `validated`.
- The transition remained persisted after a full page refresh.

## Automated verification

- Site production build: passed.
- Site tests: **6 passed, 0 failed**.
- Backend targeted tests: **57 passed, 0 failed**.
- Backend full regression: **503 passed, 0 failed**.
- Rebuilt local API container: healthy on `127.0.0.1:8080`.

## Remaining boundary

Stage 2 reviewer and lifecycle mutations are accepted locally. Publication
release remains governed by the publisher role and was not exercised because
this acceptance did not authorize releasing a scientific artifact.

The next canonical migration stage is discovery and source inspection.
