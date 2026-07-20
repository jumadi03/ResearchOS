# Traefik Ownership Migration Report

Date: 2026-07-20
Target: Hostinger VPS `srv1534304` (`76.13.20.211`)

## Decision

**TRAEFIK OWNERSHIP MIGRATION ACCEPTED.**

The production TLS reverse proxy is now owned by the ResearchOS Compose project.
No container belonging to the former n8n project remains.

## Committed source

- Git commit: `7381412014d7e4c3ea369b9971e49a76a6f50238`
- Remote commit marker: `/opt/researchos/DEPLOYED_COMMIT`
- Remote Compose SHA-256:
  `4d2032565eaa425d525ed3e2765f79e7323ae3f4f7ea80253e7743a85f30eb04`
- Traefik image digest:
  `sha256:279606d45ac2a96f6b3f2e2f978b5534afeb9b5aeda478a728dede7e8d55ac37`

The previous production Compose file was preserved at
`/opt/researchos/deploy/compose.hostinger.yaml.pre-traefik-20260720T043122Z`.

## Cutover

Cutover started at `2026-07-20T04:34:08Z`:

1. `n8n-traefik-1` was stopped while retained for rollback.
2. `researchos-traefik-1` was created from the committed ResearchOS Compose.
3. The existing external `traefik_data` certificate volume was mounted.
4. Public ResearchOS health returned `{"status":"ok"}` through the new proxy.
5. Only after that proof passed was `n8n-traefik-1` removed.

## Production evidence

Verified at `2026-07-20T04:34:41Z`:

- `researchos-traefik-1` was running on public ports 80 and 443;
- its Compose project label was `researchos`;
- no container name beginning with `n8n-` remained;
- the retained ACME store was 35,619 bytes;
- HTTP returned 301 to the HTTPS entry point;
- HTTPS returned HTTP 200;
- API health returned `{"status":"ok"}`;
- production monitor status was `passed` with no failures;
- PostgreSQL remained at schema 41 with 325 canonical objects and 6 workspace
  users; and
- the public UI survived a browser reload and displayed the expected ResearchOS
  login boundary.

The filesystem remained at 5.1 GB used and 91 GB available.

## Remaining compatibility name

The Docker network is still named `n8n_default` because changing the live
network was not required to remove n8n and would have added avoidable routing
risk. It contains the ResearchOS API and Traefik endpoints only. The name is a
compatibility identifier, not a running n8n application.

## Hostinger Docker Manager reconciliation

After the container migration, the user's refreshed hPanel still displayed an
`n8n` project with one container and ResearchOS with eight. This observation
was treated as a production finding rather than dismissed as browser cache.

Live inspection at `2026-07-20T04:40:13Z` showed that Docker Compose listed only
the `researchos` project, but Hostinger's legacy catalog directory
`/docker/n8n` still contained the original `docker-compose.yml` defining
Traefik, n8n, and WAHA. hPanel was therefore retaining the project from its
catalog definition rather than current Docker container state.

The complete `/docker/n8n` directory, including its private environment file,
was moved without deletion to:

`/opt/n8n-retirement-backup/20260720T042147Z/hostinger-project`

Post-move evidence confirmed:

- `/docker` contained no project directory;
- `docker compose ls -a` listed only `researchos`;
- no `n8n-*` container existed; and
- the public ResearchOS API remained healthy.
