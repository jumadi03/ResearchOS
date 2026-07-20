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
