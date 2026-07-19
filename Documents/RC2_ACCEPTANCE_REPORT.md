# ResearchOS v0.5.0-rc.2 Acceptance Report

Date: 2026-07-19  
Candidate: `v0.5.0-rc.2`  
Tagged commit: `38913be7802afeff5baa2c0b382d4447bf8072ef`  
Decision: **NOT ACCEPTED — SUPERSEDE WITH RC.3**

## Scope

This acceptance review covered the canonical UI build contract, the live local
ResearchOS backend, all six local human roles, SGF-020C consequential-research
read paths and transactional controls, and backup/restore readiness.

The review did not authorize merge, GitHub Release creation, public deployment,
or a claim of independent human approval.

## Baseline evidence

- The tag and commit resolved to the same revision.
- The release bundle reported 487 passing backend tests, one passing canonical
  UI test, database schema version 41, and installed package version
  `0.5.0rc2`.
- All six GitHub architecture quality gates passed for the tagged commit.
- Release checksums matched, provenance matched the tagged commit, and the
  source archive contained no local secret files.

## Acceptance execution

### Canonical UI

- The Vinext production build completed successfully.
- The rendered HTML smoke test passed.
- Interactive browser control and its local kernel were reverified on
  2026-07-19 and operated successfully.
- The canonical production UI at
  `https://researchos-ilmiah.jumadi03.chatgpt.site/` loaded with the expected
  `ResearchOS — Ruang Kerja Ilmiah` title and rendered without visible
  clipping, overlap, missing glyphs, or broken component geometry in the
  inspected desktop viewport.
- The visible trust-boundary content correctly stated that machine assistance
  is advisory and that human researchers retain decision authority.
- The deployed UI reported `Backend belum tersedia` and
  `Permintaan gagal (404)` while checking the ResearchOS session. It did not
  display fabricated project data and instead remained in its explicit
  fail-closed empty state.
- The `Periksa kembali` control was present, enabled, and interactive. Invoking
  it repeated the backend check and retained the explicit HTTP 404 failure
  state. The ResearchOS home link also navigated correctly to `#top`.
- No browser console warning or error was captured during the inspected load
  and retry interaction.

This closes the earlier acceptance-environment limitation for browser
inspection. It does not establish live end-to-end UI/backend readiness because
the canonical deployment's session request returned HTTP 404. It also does not
change the RC.2 rejection, which remains independently required by the tagged
SGF-020C revalidation defect.

### Human authentication

All six local accounts successfully completed login, authenticated-session
inspection, role verification, and CSRF-protected logout:

- discoverer;
- auditor;
- reviewer;
- indexer;
- publisher; and
- admin.

No credentials were printed or recorded in this report.

### Consequential-research governance

The tagged candidate exposed the profile endpoint successfully, but
`GET /knowledge/governance/consequential/revalidation` returned HTTP 500 when
`project_id` was omitted.

Root cause:

```text
psycopg.errors.IndeterminateDatatype:
could not determine data type of parameter $1
```

The optional filter used an untyped null parameter:

```sql
WHERE (%s IS NULL OR project_id=%s)
```

The local post-tag patch applies an explicit PostgreSQL text cast:

```sql
WHERE (%s::text IS NULL OR project_id=%s)
```

After the patch:

- seven targeted SGF-020C regression tests passed;
- the complete backend regression suite passed with 487 tests;
- the canonical Vinext production build completed successfully and its
  rendered-HTML test passed;
- the profile endpoint passed;
- the revalidation endpoint passed with `fail_closed: true`;
- the transactional PostgreSQL verifier passed and rolled back its test data;
- quorum, ethics, authority qualification, conflict, freshness, independent
  release authority, and fabricated quorum-result rejection were exercised.

Because this fix is not present in tagged commit `38913be`, it cannot change the
acceptance result for `v0.5.0-rc.2`.

### Publication controls

The transactional consequential verifier confirmed that a publication-release
decision is not ready before the required ethics, qualification, conflict, and
quorum conditions are met, and that database-derived readiness passes only
after those conditions are satisfied.

The immutable publication gate remains covered by the passing PostgreSQL/MinIO
integration and schema quality gates. No permanent acceptance-only publication
records were inserted into the live canonical database.

### Backup and recovery

The first recovery read correctly returned `recovery_ready: false` because the
latest post-rotation backup did not yet have matching restore evidence.

A new isolated restore drill was then completed:

- run ID: `8c550738-dd3f-46d5-8e85-7e2d3a1b853f`;
- verification ID: `c01ff18d-9614-4119-907e-3ece3aff4920`;
- active target touched: false;
- restore cleanup: verified.

Final recovery state:

- backup integrity ready: true;
- restore verified: true;
- restore fresh: true;
- recovery ready: true.

PostgreSQL and MinIO remained healthy, the API returned HTTP 200, and the
worker remained running.

## Acceptance decision

`v0.5.0-rc.2` is rejected as the release candidate because its tagged code has
a reproducible HTTP 500 on the SGF-020C revalidation endpoint.

The local patch resolves the defect and passes targeted acceptance checks.
The next candidate must:

1. include the typed-null query fix and regression test;
2. run the complete backend and canonical UI test suites;
3. rebuild release artifacts with provenance bound to the new commit;
4. receive a new immutable tag, `v0.5.0-rc.3`;
5. repeat the acceptance smoke test; and
6. remain unpublished pending independent human approval.
