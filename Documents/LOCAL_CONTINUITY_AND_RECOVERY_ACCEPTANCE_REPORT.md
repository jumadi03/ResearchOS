# ResearchOS Local Continuity and Recovery Acceptance

Date: 2026-07-19  
Target: local ResearchOS stack and isolated restore-drill stack  
Status: **ACCEPTED**

## Baseline

- Canonical DOI: `10.3389/fdata.2022.971974`
- Document ID: `7bcbbd0b-f825-4840-8f0d-7db1f16f2a6e`
- Representation checksum:
  `81fd706a75ed80bda68c15b29af06a11c30d5d4e0c3b0df151b593193b389b5a`
- PDF size: 660,139 bytes
- Evidence objects: 5
- Evidence review events: 1
- Reviewed evidence projection: `rejected`

## Restart continuity

The controlled continuity probe restarted PostgreSQL, MinIO, the API, and the
worker. PostgreSQL system identity, schema version 41, all six workspace
accounts, and the MinIO sentinel were identical before and after restart. The
sentinel was removed successfully.

The canonical document ID, PDF checksum and size, evidence count, review-event
count, and `rejected` projection remained unchanged. In the browser, the local
workspace reconnected, the pending reviewer queue remained at five, and the
rejected evidence did not return.

Machine-readable evidence:
`Documents/LOCAL_CONTINUITY_RUNTIME_REPORT.json`.

## Backup and isolated restore

- Backup stamp: `20260719T144623Z`
- Backup status: `completed`
- Backup integrity: verified
- Manifest hash:
  `88410efe64212a6e10e6738f3bc8b19c9a3ca4f1406c484b1fdd758e541c8ecf`
- Restore target: isolated PostgreSQL and MinIO containers on an internal
  network with temporary storage
- Active target touched: false
- Restore outcome: `verified`
- Cleanup verified: true
- PostgreSQL: 320 canonical objects, schema version 41
- MinIO: 22 objects with hashes and sizes verified
- Knowledge: 430 files verified
- Configuration: secret values absent and allowlist verified
- Migration: 42 files verified
- Architecture: empty tree verified

The restore report was signed with the trusted Ed25519 key
`restore-ed25519-24a827b8beb07e99`. Signature verification passed and the
report was admitted idempotently to the immutable
`backup_restore_verifications` ledger as verification
`048c1c88-1c72-48a6-b20f-02ec385d0213`.

Signed evidence:
`deploy/restore/reports/restore-drill-continuity-20260719T144623Z.json`.

## Operational note

The first restore invocation was blocked safely before restore execution
because its report filename did not match the required
`restore-drill-*.json` allowlist. The invocation was repeated with a canonical
filename and passed. This confirms the output-path control fails closed.

## Acceptance decision

Local PostgreSQL and MinIO persistence, browser-visible reviewer state, backup
construction, isolated restore, component integrity, cleanup, signed
attestation, and immutable ledger admission all passed. The local continuity
and recovery requirement is accepted.

Full AI-Gateway regression after the drill: **502 passed**.
