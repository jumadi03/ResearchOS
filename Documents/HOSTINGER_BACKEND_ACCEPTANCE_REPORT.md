# ResearchOS Hostinger Backend Acceptance Report

Date: 2026-07-20

## Decision

**BACKEND DEPLOYMENT ACCEPTED FOR AUTHENTICATED PRODUCTION ACCEPTANCE.**

The ResearchOS backend is independently reachable over HTTPS at
`https://researchos-api.srv1534304.hstgr.cloud`. Existing n8n, WAHA, and Traefik
services were preserved.

## Verified deployment state

- Ubuntu 24.04 VPS at `76.13.20.211`.
- ResearchOS API, PostgreSQL, and MinIO containers are healthy.
- ResearchOS worker is running.
- Database schema version is `41`.
- Canonical object count is `325`.
- Workspace user count is `6`.
- MinIO object count is `22`.
- The HTTPS health endpoint returns `{"status":"ok"}`.
- The TLS certificate covers `researchos-api.srv1534304.hstgr.cloud`, is issued
  by Let's Encrypt, and is valid from 2026-07-20 through 2026-10-18.
- PostgreSQL and MinIO are not exposed as public host ports.

## Data restoration

The verified local backup stamped `20260720T020424Z` was restored for
PostgreSQL, MinIO, knowledge, and architecture data. Migration verification
passed at schema version 41 using the exact migration files included in that
backup.

## UI binding

Sites environment revision 1 sets `RESEARCHOS_API_ORIGIN` to the Hostinger HTTPS
origin. Owner-only Sites version 9 is deployed at
`https://researchos-ilmiah.jumadi03.chatgpt.site/`.

Fresh browser inspection reached the ResearchOS authentication boundary. The
reviewer then authenticated successfully, remained connected after refresh, and
loaded the accepted graph baseline of 84 nodes and 160 edges. Searching for
`demographic control` produced 2 nodes and 1 edge; the selected evidence,
stable-key inspector, and search state all persisted after another refresh.

## Remaining acceptance

Authenticated UI-to-backend connectivity, graph interaction, and refresh
persistence are accepted. A scientific review mutation was not performed solely
for deployment testing. No GitHub Release publication is authorized by this
deployment acceptance.
