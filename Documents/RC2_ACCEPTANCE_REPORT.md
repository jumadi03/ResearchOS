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

## Post-RC.2 infrastructure evidence — 2026-07-20

This evidence is recorded for audit continuity only and is not retroactive
acceptance of the immutable RC.2 tag.

- The canonical UI was self-hosted on the Hostinger VPS at
  `https://researchos.click`.
- Public DNS for the root and `www` resolved to VPS `76.13.20.211`.
- Trusted HTTPS, UI HTTP 200, and the UI-to-backend proxy were verified.
- The first real login exposed a UI runtime HTTP 500 when Node required
  `duplex: "half"` for a streamed request body.
- UI commit `def1c7831a05e7f4d1bdd676630f12192c16b4ac` corrected the proxy and
  added a POST-body regression test; all 13 UI tests passed.
- The exact corrective image was deployed and reported `running/healthy`.
- A real reviewer login succeeded, F5 preserved the session, and PostgreSQL
  `last_seen_at` advanced from `2026-07-20 07:14:55.640642+00` to
  `2026-07-20 07:17:03.982460+00`.
- Detailed evidence is preserved in
  `Documents/HOSTINGER_SELF_HOSTED_UI_ACCEPTANCE_20260720.md`.

These later infrastructure results do not contain the typed-null SGF-020C fix
inside tagged commit `38913be`; therefore RC.2 remains rejected and must not be
moved or relabeled.

The subsequent canonical mutation acceptance also passed on 2026-07-20:
a reviewer moved artifact `bada8f58-839b-45a1-8dde-1cf56f975841` from `draft`
to `review`; F5 preserved the new queue state; and PostgreSQL matched immutable
lifecycle event `af60c4f8-ee72-4270-bd83-5330e27de073`. This proves the later
production environment, not the immutable RC.2 candidate. RC.2 therefore
remains **NOT ACCEPTED**.

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
