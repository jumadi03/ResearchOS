# ResearchOS Local Offsite Backup Acceptance

Date: 2026-07-20  
Production source: Hostinger VPS `76.13.20.211`  
Local destination: `D:\ResearchOS\Backups\Hostinger`  
Decision: **ACCEPTED**

## Architecture

The Hostinger VPS remains the canonical active system. The local computer is an
offsite archive and recovery target:

```text
researchos.click -> VPS hot storage -> verified one-way pull -> local archive
```

The local computer does not write automatically to production. No production
record or object is deleted by this workflow.

## Backup set

The production backup service created set `20260720T075150Z` after the public
login, refresh, and audited lifecycle acceptance.

The local pull copied and verified:

- PostgreSQL custom-format dump;
- MinIO document archive;
- knowledge archive;
- architecture archive;
- configuration archive;
- migration archive;
- backup-set manifest; and
- individual SHA-256 sidecars.

The completed local set is stored at:

`D:\ResearchOS\Backups\Hostinger\20260720T075150Z`

The pull script reported:

```text
offsite-backup=passed stamp=20260720T075150Z status=copied-and-verified
```

## Restore verification

The PostgreSQL dump was restored into an isolated, temporary local
`pgvector/pgvector:pg17` container with no published network port. The restore
completed successfully.

Read-only verification of the restored database returned:

```text
schema_version = 41
canonical_objects = 325
artifact bada8f58-839b-45a1-8dde-1cf56f975841 status = review
lifecycle event af60c4f8-ee72-4270-bd83-5330e27de073 count = 1
```

This proves that the backup contains the production mutation accepted earlier
on 2026-07-20. The temporary restore container was removed after verification;
the backup files remain on disk.

The MinIO archive passed its SHA-256 checks and its tar structure was readable.
It contains the object manifest, publications, scientific representations, and
the continuity probe present at backup time.

## Automatic operation

Windows Scheduled Task:

```text
Name: ResearchOS-Hostinger-Backup-Sync
Schedule: daily at 14:30 WITA
Command: D:\ResearchOS\scripts\run_hostinger_backup_sync.cmd
State: enabled / ready
Next run: 2026-07-21 14:30 WITA
```

The task runs as the local `ROG` user in interactive mode because the SSH
private key remains inside that user's profile. The computer must be powered
on and the user logged in at the scheduled time. A missed run does not affect
production availability; the next successful run pulls the latest completed
set.

The wrapper invokes `monitor_hostinger_backup.ps1`, which first requires a
fresh, passing VPS health state and then invokes `pull_hostinger_backup.ps1`.
The pull uses a partial directory, verifies the manifest and every component,
and only then atomically promotes the set to its final directory.

Latest local monitor evidence:

```text
status = passed
monitor_schema_version = 41
canonical_object_count = 325
checked_at = 2026-07-20T07:58:08.6504473+00:00
```

## Capacity boundary

This acceptance establishes safe local archival and recovery. It does not yet
authorize automatic deletion or eviction from VPS hot storage. That later
feature requires:

1. at least two verified local/offsite copies;
2. a retention policy by object class;
3. an archive catalog with checksums and location state;
4. a tested restore-on-demand path; and
5. explicit human authorization before each initial deletion class.
