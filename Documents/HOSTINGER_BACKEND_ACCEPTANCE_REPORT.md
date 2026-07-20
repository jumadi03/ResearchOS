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

## Operational hardening

Automated operational controls were activated on 2026-07-20:

- `researchos-backup-1` runs a verified portable backup every 86,400 seconds
  with a default 14-day retention period.
- The first scheduled set, stamped `20260720T024359Z`, completed successfully.
- The backup-set manifest and all six components (PostgreSQL, MinIO, knowledge,
  architecture, configuration, and migration) passed SHA-256 verification.
- `researchos-monitor-1` checks API, MinIO, PostgreSQL, schema version, canonical
  object count, and health-state freshness every 60 seconds.
- The accepted monitor result reported API passed, MinIO passed, PostgreSQL
  passed, schema version 41, canonical object count 325, and no failures.
- The public HTTPS health endpoint remained healthy.
- Existing n8n, WAHA, and Traefik containers remained running and were not
  restarted.

The operating and recovery procedure is documented in
`Documents/HOSTINGER_OPERATIONS_RUNBOOK.md`.

## Off-VPS backup acceptance

The completed production set `20260720T024359Z` was copied to the local
secondary location
`D:\ResearchOS\Backups\Hostinger\20260720T024359Z`.

- The local set contains 14 files totaling 19,116,718 bytes.
- The manifest checksum, manifest component hashes, and all component sidecar
  checksums matched before the partial directory was promoted.
- The copied set excludes the Hostinger environment file, SSH key, API tokens,
  and workspace passwords.
- A second run returned `status=already-present` without duplicating the set.
- Windows task `ResearchOS-Hostinger-Offsite-Backup` is registered in `Ready`
  state and runs daily at 11:30 local time with start-when-available enabled.
- Local verified sets have a default 30-day retention period.

## Off-VPS restore-drill acceptance

The local set `20260720T030625Z` passed a full isolated restore drill. The drill
used temporary PostgreSQL and MinIO targets on an internal-only Docker network;
the production target was not touched.

- Outcome: `verified`.
- PostgreSQL restore completed with schema ledger verification.
- Schema version: 41.
- Canonical object count: 325.
- MinIO object count: 22, with sizes and hashes verified.
- Knowledge tree: 452 files, manifest verified.
- Architecture tree: 0 files, empty tree manifest verified.
- Migration tree: 42 files, manifest verified.
- Recovery configuration: 3 allowlisted files, structurally valid, no secret
  values.
- Cleanup: verified.
- Attestation: Ed25519, key ID
  `restore-ed25519-24a827b8beb07e99`.
- Restore report content hash:
  `909da2218b8f0c99277f6c6f444d42c5810b5fcec873da972845d72afe6b0211`.

The public production health endpoint remained healthy after the local drill.

## Source-volume reconciliation

The local and Hostinger knowledge sources were compared after the first
successful off-VPS drill:

- The local knowledge and architecture roots contained no legacy
  `.researchos-tree-manifest.txt` control files.
- Hostinger contained a 165,238-byte legacy knowledge control manifest and an
  empty architecture control manifest.
- The knowledge control manifest was recorded with SHA-256
  `c24a83a81616f950e3051733828497954216c08a8e0da961d8c9c4ec2a6c14a1`
  before both control files were removed.
- No scientific object, document, database row, or MinIO object was removed.

Post-cleanup backup `20260720T031629Z` was copied locally and passed another
complete isolated restore drill:

- Outcome: `verified`.
- Schema version: 41.
- Canonical object count: 325.
- MinIO object count: 22.
- Knowledge files: 452.
- Migration files: 42.
- Cleanup and Ed25519 attestation: verified.
- Restore report content hash:
  `7d5c78daba6e9850bb6f28534351426e3c12f3e1493d636c519dda36cd1c9b2f`.
- Manifest hash:
  `28ef70cfc21ba96287fd2acf6f0376ae0322dfff99ed180ab483e93d539ed276`.

The production monitor remained `passed` with schema 41 and 325 canonical
objects after reconciliation.
