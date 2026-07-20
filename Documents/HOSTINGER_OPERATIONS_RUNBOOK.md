# ResearchOS Hostinger Operations Runbook

Date: 2026-07-20

## Operating baseline

- Application directory: `/opt/researchos`
- Compose file: `/opt/researchos/deploy/compose.hostinger.yaml`
- Public API health: `https://researchos-api.srv1534304.hstgr.cloud/health`
- PostgreSQL, MinIO, backup storage, and health state remain private Docker
  volumes.
- Existing n8n, WAHA, and Traefik services are outside the ResearchOS Compose
  project and must not be removed by ResearchOS operations.

## Automated backup

The `researchos-backup-1` container creates a portable, hash-bound backup set
every 86,400 seconds (daily) and retains completed files for 14 days by default.
Each set contains PostgreSQL, MinIO documents, knowledge, architecture,
non-secret recovery configuration, and migration files.

Inspect the latest backup:

```sh
cd /opt/researchos/deploy
docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml logs --tail=100 backup
docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml exec backup sh -lc \
  'ls -1t /backups/backup-set-*.json | head -1'
```

Verify every checksum in the newest set before copying it off the VPS. Never
copy `stack.hostinger.env` into a backup or support bundle.

## Health monitoring

The `researchos-monitor-1` container checks every 60 seconds:

- the internal API health endpoint;
- the internal MinIO health endpoint;
- PostgreSQL connectivity;
- schema version 41; and
- the canonical object count.

Inspect the current state:

```sh
cd /opt/researchos/deploy
docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml exec monitor \
  cat /state/health.json
docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml ps
```

A healthy monitor has container state `healthy`, report status `passed`, and a
recent `checked_at` timestamp.

## Recovery procedure

1. Stop writes to ResearchOS while preserving the VPS and backup volumes.
2. Select a completed `backup-set-*.json` and verify its own SHA-256 file.
3. Verify the SHA-256 of every component named by the manifest.
4. Restore first into the isolated restore-drill stack under `deploy/restore`.
5. Confirm schema version, canonical object count, MinIO inventory, knowledge
   files, and architecture files.
6. Admit the signed restore report only after the isolated drill passes.
7. Schedule the production restore, record the operator and reason, then restore
   the exact verified set.
8. Start ResearchOS and require API, database, MinIO, worker, monitor, login,
   graph, and refresh-persistence checks to pass.

Never alter recorded migration checksums to force a restore through its guard.
Use the exact migration archive included in the verified backup set.

## Off-VPS copy

The local Windows task runs `Scripts/pull_hostinger_backup.ps1` and stores
verified sets under `D:\ResearchOS\Backups\Hostinger\<backup-stamp>`. The
directory is excluded from Git. The pull accepts a set only after the manifest,
every component, and every sidecar checksum agree. Local copies are retained for
30 days by default.

Run an additional copy manually:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File D:\ResearchOS\Scripts\pull_hostinger_backup.ps1
```

The off-VPS copy deliberately excludes `stack.hostinger.env`, SSH keys, API
tokens, and user passwords.

The first backup proven restorable by the isolated off-VPS drill is
`20260720T030625Z`. Earlier sets `20260720T024359Z` and
`20260720T025833Z` remain checksum-valid historical artifacts but must not be
selected for recovery because their filesystem control-manifest contract was
not portable. Recovery selection must require a successful signed restore-drill
report, not checksum validity alone.

## Incident priorities

1. Preserve data and backup volumes.
2. Capture `docker compose ps` and the last 200 log lines for the affected
   ResearchOS service.
3. Confirm disk capacity before restarting a database or storage service.
4. Restart only the affected ResearchOS service when possible.
5. Do not restart or reconfigure n8n, WAHA, or Traefik unless evidence shows the
   incident belongs to those services.
