# ResearchOS v0.5.0-rc.4 Acceptance Report

Date: 2026-07-19
Candidate: `v0.5.0-rc.4`
Tagged commit: `b493fd7ba9646336a22300873b82bb70d086097b`
Decision: **TECHNICALLY ACCEPTED AS THE CONSOLIDATED LOCAL IMPLEMENTATION BASELINE**
Publication: **NOT AUTHORIZED**

## Scope

This acceptance verifies that the backend release, canonical Sites UI, test
evidence, and release artifacts form one traceable implementation baseline.
It does not publish a GitHub Release, push a tag, authorize production data
access, perform canonical UI cutover, or grant independent scientific
approval.

## Immutable lineage

- `v0.5.0-rc.3` remains unchanged at
  `d1f9a6ff7bb3f04ce782cf20ef88c37bbd32bf16`.
- `v0.5.0-rc.4` is an annotated local tag resolving to the commit stated
  above.
- The RC.4 provenance document records the same root revision as the tag.

## Verification results

- Backend regression: **491 passed, 0 failed**.
- Canonical UI: production build passed.
- Canonical UI rendered-HTML regression: **2 passed, 0 failed**.
- Installed backend package version: `0.5.0rc4`.
- Database schema baseline: `41`.
- Release artifact build: passed with six outputs.
- SHA-256 verification: all recorded artifact checksums matched.
- Source archive inspection: `deploy/canonical-ui.lock.json` is included.

## Cross-repository UI binding

The RC.4 release baseline and provenance bind the canonical target UI to:

- source commit:
  `aa3d2eafa0fdbf929beece0cf5ff905482c4df56`;
- saved Sites version: `7`;
- production URL:
  `https://researchos-ilmiah.jumadi03.chatgpt.site`;
- build contract: `vinext`;
- passing UI tests: `2`; and
- operational status: `canonical_target_not_cutover`.

This closes the reconstruction gap identified in the RC.3 acceptance report.
The production URL identifies the canonical target interface, but the status
explicitly prevents it from being mistaken for a completed production-data
cutover.

## Release artifacts

The local artifact set contains:

1. source archive;
2. Python wheel;
3. CycloneDX SBOM;
4. release baseline;
5. provenance statement; and
6. SHA-256 checksum manifest.

The artifacts remain local and unpublished.

## Acceptance decision

RC.4 is accepted as the consolidated local implementation baseline for
subsequent engineering work. The acceptance is technical and reproducibility
focused; it does not authorize GitHub publication, public backend exposure,
production cutover, or scientific claims.

Any publication decision must separately confirm repository cleanliness,
remote tag absence, release-note approval, artifact attachment, deployment
policy, secret handling, and operator authorization.
