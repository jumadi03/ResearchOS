# ResearchOS Hostinger Security Hardening Report

Date: 2026-07-20

## Decision

**HOST SECURITY HARDENING ACCEPTED.**

The Hostinger VPS remains operational after moving routine administration and
backup automation away from direct root SSH.

## Verified controls

- Routine SSH access uses the existing `ubuntu` account and the dedicated
  ResearchOS Ed25519 key.
- `ubuntu` can perform required administration through non-interactive `sudo`.
- Direct root SSH is rejected.
- SSH password and keyboard-interactive authentication are disabled.
- Public-key authentication is enabled.
- Maximum SSH authentication attempts are limited to three.
- SSH access is restricted to the `ubuntu` account.
- UFW is active with default deny for inbound and routed traffic.
- Only TCP ports 22, 80, and 443 are allowed publicly for IPv4 and IPv6.
- n8n port 5678 and WAHA port 3000 remain bound to loopback.
- PostgreSQL and MinIO have no public host ports.
- Unattended security upgrades remain enabled.

The effective SSH policy is tracked in
`deploy/security/00-researchos-hardening.conf`. Its early numeric prefix is
intentional because OpenSSH uses the first effective value when processing the
main configuration and included drop-ins.

## Service acceptance after hardening

- A fresh key-only `ubuntu` SSH session succeeded.
- Root SSH failed with public-key denial as intended.
- ResearchOS public health returned `{"status":"ok"}`.
- n8n returned HTTP 200 through HTTPS.
- WAHA returned HTTP 401 on its loopback endpoint, confirming that the service
  was reachable locally but protected.
- All ResearchOS, n8n, WAHA, and Traefik containers remained running.
- The production monitor remained `passed`, with schema version 41, 325
  canonical objects, and no failures.

## Backup continuity acceptance

The local backup scripts were migrated from `root@host` to
`ubuntu@host` plus `sudo` for Docker access.

- PowerShell syntax validation passed for both scripts.
- Six targeted deployment and security regression tests passed.
- The manual monitor and offsite-backup run passed against backup
  `20260720T031629Z`.
- Windows task `ResearchOS-Hostinger-Offsite-Backup` completed with result `0`,
  returned to `Ready`, and retained its next daily run at 11:30 local time.

## Recovery boundary

The Hostinger console and root password remain the out-of-band recovery method
if the SSH key or firewall configuration is damaged. The root password must
remain outside source control, documentation, logs, and support messages.

No Git tag was moved and no GitHub Release was published.
