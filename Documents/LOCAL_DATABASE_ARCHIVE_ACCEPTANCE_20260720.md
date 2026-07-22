# Local Database Archive Acceptance — 2026-07-20

## Scope

This report is local evidence only. No VPS or production service was accessed
or changed.

ResearchOS now has a separate PostgreSQL archive service on the local computer.
The archive script verifies the selected off-VPS backup checksum, restores it
into a generation-specific database, verifies the restored schema and canonical
object count, and records the generation in an append-only local catalog.

## Accepted generation

- Backup generation: `20260720T092644Z`
- Archive database: `researchos_archive_20260720t092644z`
- Dump SHA-256:
  `e67b225a29fef5c819e940a528c5089ffcd5687dc4fa3311fecf164d03627c63`
- Latest schema migration: `42`
- Canonical objects read back: `325`
- Local listener: `127.0.0.1:5433`
- Persistent Docker volume: `researchos_postgres_archive_data`

## Verification

1. The backup manifest and PostgreSQL dump checksum matched.
2. The dump restored successfully into the generation-specific archive
   database.
3. The restored database reported schema migration 42 and 325 canonical
   objects.
4. A second archive run was idempotent and returned the same checksum, schema,
   and object count.
5. The archive PostgreSQL service was restarted; the restored database still
   contained 325 canonical objects.
6. An attempted catalog update was rejected with
   `local database archive ledger is immutable`.
7. The local archive contract tests passed.
8. The backend regression suite passed: 528 tests.

## Transparent failure history

The first restore attempt stopped before creating or restoring the generation
database because the archive-catalog function delimiter was incorrectly
escaped. The delimiter was corrected, the contract test was strengthened, and
the restore then passed. No development or production database was modified by
the failed attempt.

## Operational boundary

This archive is a safety copy for local cleanup work. Creating an archive does
not itself authorize deletion. Cleanup must still identify its exact scope and
confirm the accepted archive generation before any destructive operation.

## Inactive-data vault extension

The local archive was subsequently extended to retain cleanup candidates as
immutable inactive data. Each item stores its original locator, filename,
reason, metadata, byte length, complete binary content, and SHA-256 checksum.
Restoration creates a separate file, refuses to overwrite an existing
destination, verifies the recovered checksum, and appends an immutable restore
event. The archived payload itself remains inactive and unchanged.

Accepted historical GitHub snapshot:

- item ID: `ad1d078c-c00f-4cae-a57c-66e869dbe65d`;
- kind: `legacy_github_bundle`;
- source: `legacy-github://remote-tracking-refs`;
- captured references: 13;
- size: 1,251,106 bytes;
- SHA-256:
  `cb0cc0ad616d4cb5dd9f945abe25decaa836e27d214f3b4cdd5ab95e97413cb7`;
- Git bundle verification: complete history, passed; and
- restored-copy verification: passed.

The snapshot is historical evidence, not an active source and not an
instruction to merge the old GitHub branches. At capture time,
`legacy-github/main` was an ancestor of the local ledger and was 76 commits
behind it.

A disposable stale-file fixture was also admitted as item
`8409994d-20e5-4f98-81d3-44112ac1c871`, removed from its source location,
restored into the separate recovery area, and verified against its archived
checksum. Both inactive items and both restore events remained present after
the archive database restarted.

The first stale-file attempt failed before admission because the installed
Windows PowerShell runtime did not provide `System.IO.Path.GetRelativePath`.
Workspace-relative path handling was replaced with a case-insensitive,
root-bounded implementation and the complete round trip then passed.

Future cleanup uses `Scripts/archive_inactive_data.ps1` before removing an
approved stale file. Recovery uses `Scripts/restore_inactive_data.ps1` with an
explicit unused destination. Neither script decides that a file is stale or
authorizes cleanup by itself.

## VPS completion receipt

Reported to the canonical Hostinger VPS on 2026-07-20 at approximately 22:22
WITA. This reporting operation did not deploy the local archive database,
change the production application source, recreate a container, or mutate the
production PostgreSQL or MinIO data.

The following completion evidence was installed under the existing root-only
directory `/opt/researchos/deploy-backups`:

- `researchos-ledger-a1ba4d2.bundle`
  - commit: `a1ba4d2255d7e9c4119d13a3add7f797be687544`;
  - size: 1,386,566 bytes;
  - SHA-256:
    `7a04c1515e275348a49d9645c7b6615c0c2a8f174933871a7cfad334313b0e10`;
  - bundle verification on the VPS: complete history, passed.
- `LOCAL_DATABASE_ARCHIVE_ACCEPTANCE_20260720.md`
  - size at initial report: 4,082 bytes;
  - SHA-256 at initial report:
    `fb49f61ffde9b1c2fa7189639ddea6a2d85d6622b30f6a5e7c86a504f253d1b8`.

Both files were observed as owner `root`, group `root`, mode `0600`; their
parent directory was owner `root`, group `root`, mode `0700`.

The first two remote bundle-verification commands were preserved as failed
observations. The first could not enter `/opt/researchos` as the unprivileged
administrative user. The second ran as root there but found no `.git`
repository because production is deployed from a source archive. Verification
then passed from a temporary isolated bare repository on the VPS, and that
temporary directory was removed.
