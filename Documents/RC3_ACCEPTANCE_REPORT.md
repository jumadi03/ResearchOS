# ResearchOS v0.5.0-rc.3 Acceptance Report

Date: 2026-07-19  
Candidate: `v0.5.0-rc.3`  
Tagged commit: `d1f9a6ff7bb3f04ce782cf20ef88c37bbd32bf16`  
Decision: **NOT ACCEPTED AS CONSOLIDATED IMPLEMENTATION BASELINE**

## Scope

This review evaluated whether RC.3 closed the RC.2 defect and whether its
release evidence bound every component required to reproduce the accepted
ResearchOS implementation baseline.

The review did not move or replace an existing tag, publish a GitHub Release,
authorize public operation, or claim independent scientific approval.

## Verified evidence

- The annotated `v0.5.0-rc.3` tag resolves to the stated immutable commit.
- The PostgreSQL nullable-filter fix and its regression assertion are present
  in the tagged source.
- The complete tagged backend suite passed with 487 tests.
- The release wheel reports installed version `0.5.0rc3`.
- The source archive, wheel, SBOM, baseline, provenance, and checksum manifest
  were generated for RC.3 and their recorded provenance resolves to the tagged
  commit.
- The SGF-020C profile, revalidation, transactional publication controls, and
  local recovery evidence had passed the preceding acceptance execution.

## Acceptance gap

RC.3 records one passing canonical UI test in its release baseline, but the
canonical target UI is maintained in a separate Sites repository that is
excluded from the root source archive. The RC.3 provenance does not identify
the UI repository commit, saved Sites version, deployment identity, or
operational cutover status.

Consequently, the exact UI source represented by the RC.3 UI-test count cannot
be reconstructed from the tagged release evidence alone. A downstream
implementer can reproduce the backend release but cannot determine which
canonical target UI revision belongs to the same baseline.

Post-tag work also introduced the explicit Sites backend-proxy boundary and the
profile-gated authenticated public-origin tunnel contract. Those changes are
not defects in the immutable RC.3 tag, but they must not be attributed to RC.3.

## Decision

RC.3 successfully fixes the defect that rejected RC.2, but it is not accepted
as the consolidated long-term implementation baseline because its
cross-repository UI provenance is incomplete.

The next candidate must:

1. preserve RC.3 and all earlier tags unchanged;
2. include a versioned canonical-UI lock manifest;
3. bind the exact Sites source commit, saved version, deployment URL, test
   count, and pre-cutover operational status;
4. include that manifest in release baseline and provenance generation;
5. pass the complete backend and canonical UI suites;
6. rebuild deterministic release artifacts from a clean commit;
7. receive a new immutable candidate tag; and
8. remain unpublished pending a separate human release decision.
