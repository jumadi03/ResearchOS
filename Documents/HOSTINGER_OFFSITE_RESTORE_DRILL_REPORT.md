# ResearchOS Hostinger Off-VPS Restore Drill

Date: 2026-07-20

Backup stamp: `20260720T030625Z`

## Decision

**VERIFIED — RESTORABLE IN AN ISOLATED TARGET.**

The backup copied from Hostinger to local secondary storage was restored into
temporary PostgreSQL and MinIO services attached only to an internal Docker
network. No active production target was touched.

## Verified evidence

| Component | Result |
| --- | --- |
| PostgreSQL | Restored; schema ledger verified; schema 41; 325 canonical objects |
| MinIO | 22 objects; size and content hashes verified |
| Knowledge | 452 files; tree manifest verified |
| Architecture | Empty canonical tree; manifest verified |
| Migration | 42 files; tree manifest verified |
| Configuration | 3 allowlisted files; structurally valid; secrets absent |
| Cleanup | Temporary database, bucket, containers, and network cleaned |
| Attestation | Ed25519 signature created with trusted restore key |

Report content hash:
`909da2218b8f0c99277f6c6f444d42c5810b5fcec873da972845d72afe6b0211`

Manifest hash:
`20aa22e1627ce394100887858d7a776c6b62661b269259f8feab359c1c0895a6`

## Corrections discovered by the drill

The drill first identified two portability defects and failed closed:

1. Hostinger configuration files were archived under deployment-specific names
   instead of the portable recovery allowlist names.
2. A previous `.researchos-tree-manifest.txt` control file was included when
   generating the next tree manifest, then overwritten by the new manifest.

Both contracts were corrected and covered by regression tests. Historical sets
`20260720T024359Z` and `20260720T025833Z` must not be used for recovery despite
having valid transport checksums. The corrected set `20260720T030625Z` is the
first Hostinger backup with verified restore evidence.
