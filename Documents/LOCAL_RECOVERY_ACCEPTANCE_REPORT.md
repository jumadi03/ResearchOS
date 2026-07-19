# ResearchOS Local Recovery Acceptance Report

Date: 2026-07-19
Scope: one-machine local implementation
Decision: **ACCEPTED — ISOLATED RECOVERY READY**

## Safety boundary

The acceptance used the canonical isolated restore-drill controller. It did
not restore over the active PostgreSQL database, active MinIO buckets, or
local user workspace. Temporary PostgreSQL and MinIO targets were destroyed
after verification.

## Execution

- Operator identity: `local-operator-acceptance`
- Controller result: `completed`
- Lease run:
  `b56d7154-f14a-4a56-8cd1-f936a90453aa`
- Selected backup:
  `d1515483-7e28-4d4d-87d1-dbd11f93ed0d`
- Admitted verification:
  `0742d82e-f75f-4119-a1d4-7f7e1013df3e`
- Signed report content hash:
  `ce7a56665e97478463fc3ad2333eaf09bdf7671cf6f1d2e377cef974f11aa821`

PostgreSQL selected the eligible backup. The operator did not provide a
backup path, manifest, restore target, signing key, report path, database URL,
or storage credential.

## Live recovery projection

After signed evidence admission, the administrator-only recovery projection
reported:

- latest backup status: `completed`;
- backup integrity ready: `true`;
- latest restore outcome: `verified`;
- restore signature and trust valid: `true`;
- restore evidence fresh: `true`; and
- recovery ready: `true`.

The administrator session used to inspect the projection was logged out after
the check. No credentials or session values are recorded in this report.

## Decision

The current local ResearchOS installation is accepted as recoverable from its
latest eligible backup using the isolated, signed, and ledger-admitted
recovery workflow.

This acceptance does not authorize destructive restoration over active data.
An actual disaster recovery operation still requires a separately authorized
operator procedure, explicit target selection, and preservation of the
affected source volumes.
