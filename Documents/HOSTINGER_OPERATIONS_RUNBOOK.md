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

## Administrative access and firewall

Routine administration uses the dedicated `ubuntu` account and the ResearchOS
SSH key:

```powershell
ssh -i $HOME\.ssh\researchos_hostinger_ed25519 ubuntu@76.13.20.211
```

Use `sudo` for Docker and operating-system administration. Direct root SSH,
password SSH, and keyboard-interactive SSH are disabled. The Hostinger console
and its root password are retained only as an out-of-band recovery path; do not
store that password in this repository or send it through support messages.

UFW denies unsolicited inbound and routed traffic. Only these public ports are
allowed:

- `22/tcp` for key-only SSH;
- `80/tcp` for HTTP redirection and certificate handling; and
- `443/tcp` for HTTPS.

n8n on port 5678 and WAHA on port 3000 remain bound to loopback. PostgreSQL and
MinIO remain private Docker services. Before changing SSH or firewall rules,
keep one verified `ubuntu` session open and prove a second key-only session can
connect.

Inspect the effective controls:

```sh
sudo sshd -T | grep -E \
  'permitrootlogin|passwordauthentication|kbdinteractiveauthentication|maxauthtries|allowusers'
sudo ufw status verbose
sudo ss -lntup
```

## Automated backup

The `researchos-backup-1` container creates a portable, hash-bound backup set
every 86,400 seconds (daily) and retains completed files for 14 days by default.
Each set contains PostgreSQL, MinIO documents, knowledge, architecture,
non-secret recovery configuration, and migration files.

Inspect the latest backup:

```sh
cd /opt/researchos/deploy
sudo docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml logs --tail=100 backup
sudo docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml exec backup sh -lc \
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
sudo docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml exec monitor \
  cat /state/health.json
sudo docker compose --env-file stack.hostinger.env -f compose.hostinger.yaml ps
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
30 days by default. Both the pull and monitor use `ubuntu` over key-only SSH,
then invoke the narrowly required Docker operations through `sudo`.

Run an additional copy manually:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File D:\ResearchOS\Scripts\pull_hostinger_backup.ps1
```

The off-VPS copy deliberately excludes `stack.hostinger.env`, SSH keys, API
tokens, and user passwords.

The scheduled task runs `Scripts/monitor_hostinger_backup.ps1`, which requires a
recent passing Hostinger monitor state and a completed backup no older than 36
hours before invoking the checksum-bound pull. A successful run updates
`D:\ResearchOS\Backups\Hostinger\status\latest.json`. A failure:

- returns a failed Windows task result;
- writes a durable incident to
  `D:\ResearchOS\Backups\Hostinger\alerts\latest.json`; and
- attempts to show a Windows message to the signed-in user.

The first backup proven restorable by the isolated off-VPS drill is
`20260720T030625Z`. Earlier sets `20260720T024359Z` and
`20260720T025833Z` remain checksum-valid historical artifacts but must not be
selected for recovery because their filesystem control-manifest contract was
not portable. Recovery selection must require a successful signed restore-drill
report, not checksum validity alone.

After removing the legacy root control manifests from the Hostinger knowledge
and architecture volumes, backup `20260720T031629Z` passed the same complete
drill and is the preferred recovery set. The local knowledge and architecture
sources were already free of those legacy control files.

## Incident priorities

1. Preserve data and backup volumes.
2. Capture `docker compose ps` and the last 200 log lines for the affected
   ResearchOS service.
3. Confirm disk capacity before restarting a database or storage service.
4. Restart only the affected ResearchOS service when possible.
5. Do not restart or reconfigure n8n, WAHA, or Traefik unless evidence shows the
   incident belongs to those services.
