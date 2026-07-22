# n8n and WAHA Retirement Report

Date: 2026-07-20
Target: Hostinger VPS `srv1534304` (`76.13.20.211`)

## Authorization and scope

The user authorized removal of the currently unused n8n and WAHA workloads to
reclaim VPS disk space. Traefik and every ResearchOS service were explicitly
preserved.

## Before state

Verified at `2026-07-20T04:21:47Z`:

- root filesystem: 96 GB total, 11 GB used, 86 GB available, 11% used;
- `n8n-n8n-1`: running, restart policy `always`;
- `n8n-waha-1`: running, restart policy `always`;
- `n8n-traefik-1`: running, restart policy `always`; and
- ResearchOS public health: `{"status":"ok"}`.

## Backup

The following verified archives were created on the VPS under
`/opt/n8n-retirement-backup/20260720T042147Z`:

| Archive | Size | SHA-256 |
|---|---:|---|
| `n8n_data.tar.gz` | 2.8 MB | `106c8f311a85ce02ded48b4ece333b2b8e5d74ca249f5f85533a874a57f5623c` |
| `n8n_waha_data.tar.gz` | 103 bytes | `09aedef0aa3be355a2ecd2a23673fd4583f73e754bc7f8b91e63c226d140f1b6` |
| `n8n_waha_files.tar.gz` | 103 bytes | `09aedef0aa3be355a2ecd2a23673fd4583f73e754bc7f8b91e63c226d140f1b6` |

All three gzip/tar archives passed an integrity listing test.

## Removed

- container `n8n-n8n-1`;
- container `n8n-waha-1`;
- image `docker.n8n.io/n8nio/n8n:latest`; and
- image `devlikeapro/waha:latest`.

The original data volumes `n8n_data`, `n8n_waha_data`, and `n8n_waha_files`
remain available for recovery.

## Preserved and verified

- `n8n-traefik-1` remains running;
- `traefik_data` remains present;
- all running ResearchOS services remain running and healthy;
- ResearchOS public health returned `{"status":"ok"}`;
- ResearchOS HTTPS health returned HTTP 200; and
- the public ResearchOS UI reloaded successfully and displayed the expected
  production login boundary.

## After state

The root filesystem reported 5.1 GB used and 91 GB available, or 6% used. The
operation therefore reclaimed approximately 5 GB while retaining the recovery
archives and original data volumes.

## Decision

**N8N AND WAHA RETIREMENT ACCEPTED.** ResearchOS and its HTTPS routing remained
available after the real production operation. The retained volumes and backup
must not be removed without a separate explicit decision.
