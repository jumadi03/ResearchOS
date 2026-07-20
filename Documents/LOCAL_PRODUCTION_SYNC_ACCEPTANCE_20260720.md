# Local Production Sync Acceptance — 20 July 2026

## Decision

**ACCEPTED** for the backup-and-restore synchronization model.

ResearchOS production remains authoritative on `https://researchos.click`. A fresh production backup was copied to the local computer, verified, restored into isolated local PostgreSQL and MinIO targets, and removed after verification. The active local development database was not overwritten.

## Actual targets

- Production application: `https://researchos.click`
- Production VPS: Hostinger, `76.13.20.211`
- Local application: `http://127.0.0.1:3002`
- Local API: `http://127.0.0.1:8080`
- Local backup archive: `D:\ResearchOS\Backups\Hostinger\20260720T092644Z`
- Signed restore report: `D:\ResearchOS\deploy\restore\reports\restore-drill-report.json`

## Evidence

### Production-to-local archive

- Backup stamp: `20260720T092644Z`
- Offsite copy: `passed`, `copied-and-verified`
- Storage-tier attestation: `passed`, six components
- Production active targets were not modified by the restore drill.

### Isolated local restore

- Outcome: `verified`
- PostgreSQL restore: completed
- Database schema: `42`
- Schema migration ledger: verified
- Canonical objects: `325`
- MinIO objects: `22`
- MinIO object hashes and sizes: verified
- Knowledge files: `452`
- Migration archive files: `43`
- Configuration allowlist and secret-absence checks: verified
- Cleanup: verified
- Attestation algorithm: Ed25519

### Local runtime

- API and worker rebuilt from the current local source.
- API health endpoint returned HTTP `200`.
- UI rebuilt from site revision `1d74722` and returned HTTP `200`.
- Browser acceptance confirmed the ResearchOS login form at `http://127.0.0.1:3002`.
- Local operational projection returned `passed`.
- Local monitor status returned `passed`.
- Latest locally visible backup: `20260720T092644Z`.
- Production revision marker: `477e8bc252e47aa8d609c5cc4cb9e75e0c090799`.
- Local storage-tier projection: six `hot` and six `archived_local` attestations.

### Regression

- Restore foundation tests: `10 passed`
- Full backend regression: `520 passed`

## Defect found and corrected

The first restore attempt correctly failed because historical migration ledger entries contain a mixture of LF-based and CRLF-based checksums. The archive manifest already protects exact bytes, so the migration-ledger comparison was made portable by accepting the raw checksum or its LF-normalized equivalent while still requiring an exact version and filename match.

Regression coverage was added for Windows and Linux line endings. The corrected restore completed successfully from an empty isolated target.

The local dashboard initially displayed unavailable operational facts because the API container did not mount the host status/archive paths and the Windows PowerShell status file contained a UTF-8 BOM. Read-only mounts, timestamp-directory discovery, and BOM-compatible parsing were added with regression coverage.

## Operating boundary

This acceptance proves recoverable synchronization, not a live two-way database mirror. Production continues to serve users from the VPS. The local computer stores verified backup generations and can restore them independently. This avoids exposing the home computer as a production dependency and prevents accidental overwriting of the local development database.

## Revision-marker correction

The full production marker recorded above was later found not to resolve to a
Git object. Its abbreviated value `477e8bc` resolves in the authoritative
local repository to
`477e8bcc268982c7e13a5593117c48d2b48d3b59`.
The original observation is retained for audit history; the corrected identity
is used by the production release manifest and subsequent deployments.
