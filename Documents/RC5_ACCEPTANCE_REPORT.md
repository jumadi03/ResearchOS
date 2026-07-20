# ResearchOS v0.5.0-rc.5 Acceptance Report

Date: 2026-07-20

Candidate: `v0.5.0-rc.5`

Candidate commit: `2760a6ec6123ec0cb933d84391f0fe9a1e1bc2a4`

## Decision

**TECHNICALLY ACCEPTED AS A LOCAL RELEASE CANDIDATE.**

**REPOSITORY PUBLICATION IS NOT AUTHORIZED.** RC.5 has not been pushed as a
ResearchOS repository release and has not been published as a GitHub Release.
After local acceptance, its owner-only Sites UI version was deployed without
moving the RC.5 tag.

RC.2 remains **NOT ACCEPTED**. Its tag was not moved or modified.

## Acceptance evidence

- Backend regression: **505 passed, 0 failed** in 32.15 seconds.
- Release-contract regression: **4 passed, 0 failed**.
- Canonical UI regression: **8 passed, 0 failed**.
- Canonical UI production build: **passed** with Vinext.
- Interactive local-browser acceptance: **passed**.
- Installed backend package version: `0.5.0rc5`.
- Database schema version: `41`.
- Source archive inventory: 620 tracked files and **0 temporary test entries**.
- Release artifacts, SBOM, baseline, provenance, and SHA-256 manifest were
  generated successfully.

The first full backend attempt completed 275 tests while 230 fixtures could not
start because the configured parent temporary directory did not exist. After
creating an isolated local parent directory, the unchanged suite passed
505/505. This was an execution-environment failure, not an application failure.

## Canonical UI binding

- UI source commit: `8b06689b36f8a7c6df024c8e188d51e595fac216`.
- Saved Sites version: `8`.
- Current version state: `deployed`.
- Currently deployed Sites version: `8`.
- Production target:
  `https://researchos-ilmiah.jumadi03.chatgpt.site/`.
- Operational state: `canonical_target_not_cutover`.

The accepted graph-explorer behavior and visual layout are recorded in
`Documents/LOCAL_CANONICAL_GRAPH_EXPLORER_ACCEPTANCE_REPORT.md`. RC.5 binds that
exact accepted source to a reconstructible saved Sites version.

The subsequent owner-only production deployment succeeded at the same canonical
URL. Browser inspection confirmed the new UI shell is active and correctly
fails closed with `Backend belum tersedia` because `RESEARCHOS_API_ORIGIN` is
not yet configured in the Sites runtime. No sample data or false connected
state is displayed.

## Interactive local-browser acceptance

The canonical local UI at `http://localhost:3000/` was exercised against the
local backend after the automated regression:

- The UI reached the `Terhubung` state and restored the verified reviewer
  session.
- The canonical ResearchOS project loaded with 325 scientific objects.
- The graph loaded 84 nodes and the bounded 160-edge view.
- Searching for `demographic control` reduced the view to 2 nodes and 1 edge.
- Keyboard activation opened the evidence inspector with its stable key,
  object ID, relationship summary, and audited Object Inspector link.
- After a full page refresh, the backend connection, graph search, selected
  evidence node, and stable-key inspector state were all preserved.

## Release artifact checksums

```text
8f2e73ca2af8b6f80898b1690e47e83084b1b89ce79d4cf7822417e663d50af6  ResearchOS-0.5.0-rc.5-source.zip
cf43b191492e89476faabdb5408f09cca3bf80ee71b8527c280e3f4fb5e8aa77  ResearchOS-0.5.0-rc.5.baseline.json
aa10149222b52e30eae3b32ce3ad00978e392c8ee7b17af02837c23fc5be89e1  ResearchOS-0.5.0-rc.5.cdx.json
dc1c4cfc5e184e4619239091e1db21e6af878c576108474b2b173d3981145a69  ResearchOS-0.5.0-rc.5.provenance.json
ecd7bc8286014d9d487489194f573b0e98a56360c95236ad2670804988359c0e  researchos_ai_gateway-0.5.0rc5-py3-none-any.whl
```

## Tag integrity and publication boundary

- `v0.5.0-rc.1` through `v0.5.0-rc.4` retain their existing tag objects and
  target commits.
- `v0.5.0-rc.5` is an annotated local tag resolving to the candidate commit
  stated above.
- No ResearchOS repository push was performed.
- No GitHub Release was created.
- Sites version 8 was deployed after the immutable RC.5 candidate tag was
  created; the tag was not moved.

## Remaining gate

The remaining implementation gate is a publicly reachable HTTPS backend origin
and explicit configuration of `RESEARCHOS_API_ORIGIN` in Sites. Repository tag
push and GitHub Release publication remain separate decisions and are not
authorized by this acceptance.
