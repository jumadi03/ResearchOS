# ResearchOS Tiered Storage Acceptance — 2026-07-20

## Scope

Implement a fail-closed catalog that distinguishes data retained on the
Hostinger VPS (`hot`) from a checksum-verified off-VPS copy on the local
computer (`archived_local`). This acceptance does **not** authorize deletion,
eviction, or movement of canonical production data.

## Revisions

- Backend, database, and synchronization source: `6606691ac0300b3ab322dfa8396fe7721a04776a`
- Production UI source/image: `76ae1965e8a586454676415d1aac1c70dda4f353`
- Production target: Hostinger VPS `76.13.20.211`
- Public UI: `https://researchos.click/`
- Public API: `https://api.researchos.click/`

## Local verification

Verified at 2026-07-20 16:38 WITA:

- full backend regression: `516 passed`;
- targeted backend/storage regression after final fixes: passed;
- UI production build and regression: `14 passed`;
- PowerShell attestation script syntax: passed;
- Bash migration runner syntax: passed.

## Production deployment evidence

- migration runner applied `042_tiered_storage_catalog.sql`;
- production schema version: `42`;
- `storage_tier_attestations` and `storage_tier_current` exist;
- API, UI, and monitor containers reported `healthy`;
- running UI image:
  `researchos-ui:76ae1965e8a586454676415d1aac1c70dda4f353`;
- the public `https://researchos.click/` login surface loaded through the
  browser after deployment.

## Real off-VPS attestation

The local synchronization used backup set `20260720T075150Z`. Every component
was re-hashed locally before admission. The database then accepted 12 immutable
attestations:

- `hot`: 6 rows / 6 distinct components;
- `archived_local`: 6 rows / 6 distinct components;
- `restore_required`: 0 rows;
- eviction authorization returned by the projection: `false`.

The six components are PostgreSQL, MinIO, knowledge, architecture,
configuration, and migration. Public projection locators are logical locators;
the Windows filesystem path is not exposed by the API.

## Failed observations retained

1. The first production migration attempt stopped on SQL checksum differences.
   Audit proved that `001` and `041` matched the ledger after CRLF-to-LF
   normalization. The runner now hashes normalized LF content.
2. Migrations `029`–`032` had historical post-application source drift. The
   ledger was not rewritten. Four exact historical-to-current hash pairs are
   narrowly admitted; every other mismatch still fails closed.
3. The first attestation write attempted the container default database role
   and was rejected. No row was written. The script was corrected to bind to
   the ResearchOS database identity, after which `INSERT 0 12` succeeded.
4. A local development bearer token was rejected by the public production API,
   as expected. Database persistence was verified directly. Authenticated UI
   rendering of the two new cards still requires a user production login and
   visual confirmation after refresh.

## Decision

Tiered-storage catalog and real local-backup attestation: **ACCEPTED**.

Deletion or eviction from the VPS: **NOT AUTHORIZED**. A separate restore-first
acceptance must prove recovery from the local archive before any future space
reclamation can be considered.
