# ResearchOS Operational Status Acceptance — 2026-07-20

## Scope

Production correction for the empty **Kesehatan operasional** section observed
by the user at `https://researchos.click`.

## Failed production observation

- The authenticated public UI rendered the section heading but no operational
  banner or status cards, including no **Arsip lokal terverifikasi** or
  **Penghapusan dari VPS** card.
- Repeated **Segarkan status** and browser refresh did not change the result.
- Production access logs showed both authenticated requests returning HTTP 200:
  `/knowledge/operations/status` and
  `/knowledge/operations/storage-tiers`.
- Source inspection proved that `/knowledge/operations/status` returned JSON
  `null`: its `build_operational_status(...)` return statement had accidentally
  been placed after the storage-tier endpoint's return statement and was
  unreachable.

## Correction and regression evidence

- Restored the `build_operational_status(...)` return statement to
  `operational_status`.
- Removed the unreachable statement from `storage_tier_status`.
- Added an authenticated API regression test that requires the operational
  status payload to be returned rather than `null`.
- Full backend regression: **519 passed** in **37.16 seconds** using a
  workspace-local pytest temporary directory.
- Production source commit:
  `477e8bc252e47aa8d609c5cc4cb9e75e0c090799`
  (`fix: restore operational status response`).

## Production deployment evidence

- Deployment archive SHA-256:
  `3d11857158febda06cba1755574c4f5e3fdca5c0b179e030b2ffa03f2ad08631`.
- The same checksum was observed locally and on the Hostinger VPS before
  extraction.
- Only the `researchos-api-1` service was rebuilt and recreated.
- Running API image:
  `sha256:53789dd7b573f9f83d989896ecb3d25f4ce9fb5aa26e3e34f465e93f39542529`.
- Container state after deployment: `running healthy`.
- `/opt/researchos/DEPLOYED_COMMIT`:
  `477e8bc252e47aa8d609c5cc4cb9e75e0c090799`.
- Public API health: `ok`.
- Public UI: HTTP 200 with HSTS
  `max-age=31536000; includeSubDomains; preload`.

## Production persistence evidence

The production PostgreSQL view `storage_tier_current` still contained 12 rows
after the API replacement:

- 6 `archived_local` components;
- 6 corresponding `hot` components;
- backup stamp `20260720T075150Z`;
- every archived component retained
  `{"checksum_verified": true}`.

No production database row or object-storage object was deleted or modified by
this correction. VPS eviction remains fail-closed and unauthorized.

## Acceptance state

- Backend correction: **PASSED**.
- Production deployment and health: **PASSED**.
- Production persistence: **PASSED**.
- Authenticated public UI visual confirmation: **PENDING USER REFRESH AND
  CONFIRMATION**.

## Second production observation and UI hardening

The user performed both a normal refresh and `Ctrl+Shift+R` after the backend
correction. The authenticated production UI still showed the empty section.
This failed observation remains part of the acceptance history.

Further production checks proved:

- the authenticated direct API path returned the complete operational payload;
- the authenticated UI proxy path returned the same complete payload;
- `archived_local` was 6 and `eviction_authorized` was `false` through both
  paths; and
- the user's refresh requests were visible in the real API access log with
  HTTP 200 for both endpoints.

The UI was hardened so that:

- operational and storage-tier requests settle independently;
- a failure in one cannot erase a successful result from the other;
- storage-tier cards no longer depend on the monitor payload;
- loading and error states are always visible instead of leaving silent blank
  space.

UI verification and deployment:

- UI tests: **14 passed**;
- production build: **passed**;
- UI source commit:
  `1d747220ddf5b30bc4cb3506adcb7f71aacdbf19`;
- archive SHA-256:
  `8a1b74ecfc296f44a2d9f0edf1e59cb5b313e649a0850f8f5d1f12ac1e47aaab`;
- running image:
  `researchos-ui:1d747220ddf5b30bc4cb3506adcb7f71aacdbf19`;
- running image digest:
  `sha256:6e1320426f02a21b8df428884217cbd7ec1255f2978e73cb9f1240f5bdb842a3`;
- container state: `running healthy`;
- previous public asset: `page-66UeCDH-.js`;
- new public asset: `page-B-vD-1q2.js`.

## Final authenticated visual acceptance

At 2026-07-20 17:21 Asia/Makassar, the user supplied a screenshot of the
authenticated public production UI at `https://researchos.click`. It visibly
confirmed:

- **Produksi sehat**;
- monitor: `passed`;
- backup: `20260720T075150Z`, `available`;
- disk used: `16.7%`, below the `85%` attention threshold;
- production revision: `477e8bc252e4`;
- **Arsip lokal terverifikasi: 6**, `komponen checksum-valid`; and
- **Penghapusan dari VPS: terkunci**, `restore-first, fail-closed`.

Final decision for this operational-status correction:
**ACCEPTED IN PRODUCTION**.

This acceptance does not authorize deletion of any VPS data. The next required
gate remains an isolated restore test from the local backup.
