# Local Sites-to-Backend Acceptance Report

Date: 2026-07-19  
Scope: canonical ResearchOS UI connected to the local ResearchOS backend

## Decision

**ACCEPTED for local-computer operation.**

The canonical UI can run locally and reach the ResearchOS API through its
same-origin proxy. This acceptance does not claim that the public Sites
deployment can reach a loopback-only backend.

## Configuration

- UI: `http://localhost:3003/` during acceptance (the development server chose
  the first free port).
- API origin configured in ignored `site/.env.local`:
  `http://127.0.0.1:8080`.
- A tracked `site/.env.example` documents the local configuration without
  storing credentials.
- Vite now loads `.env.local` before constructing the worker binding.
- Cloudflare Access credentials are not required for a loopback API origin.

## Browser acceptance

Interactive browser verification passed:

1. The UI changed from **Memeriksa layanan** to **Terhubung**.
2. The authenticated admin session was displayed.
3. The verified **ResearchOS** project was loaded from the backend.
4. The consequential-control section loaded backend-derived state.
5. A full page reload preserved the authenticated session and project data.
6. The verified project link opened
   `http://localhost:8080/workspace?project=researchos-default`.
7. The operational workspace retained the session, selected the ResearchOS
   project, and loaded its 320 canonical objects.

These observations confirm that the browser used the UI's same-origin proxy,
not a direct cross-origin call to port 8080.

The workspace handoff deliberately uses `localhost` on both UI and backend so
the host-scoped local session remains available when moving between ports.

## Automated verification

- Production build: passed.
- Rendered UI shell test: passed.
- Fail-closed behavior without `RESEARCHOS_API_ORIGIN`: passed.
- Local proxy forwarding and identity-header stripping: passed.
- Proxy backend-path allowlist: passed.
- Total site tests: **4 passed, 0 failed**.

## Local data boundary

Container inspection confirmed:

- API: `127.0.0.1:8080`
- PostgreSQL: `127.0.0.1:5432`
- MinIO API: `127.0.0.1:9000`
- MinIO console: `127.0.0.1:9101`

The API, PostgreSQL, and MinIO were healthy and bound to loopback only. Data
therefore remains on the local ResearchOS stack for this operating mode.

## Operational note

The UI port is selected dynamically when the preferred port is occupied. On
this machine ports 3000 through 3002 were already in use, so acceptance ran on
port 3003. The backend origin remains fixed at `127.0.0.1:8080`.

## Remaining boundary

The public UI cannot connect to `127.0.0.1:8080` on the user's computer.
Enabling public end-to-end operation remains a separate deployment task and
requires a publicly reachable protected HTTPS backend. No public deployment or
GitHub Release was created in this acceptance.
