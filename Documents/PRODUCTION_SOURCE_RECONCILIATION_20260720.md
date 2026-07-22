# ResearchOS Production Source Reconciliation — 2026-07-20

## Scope

Reconcile the authoritative local Git ledger with the running ResearchOS
services on Hostinger without using GitHub and without changing scientific
objects, lifecycle decisions, PostgreSQL schema, MinIO objects, or the
canonical UI source.

## Before state

- Verification time: 2026-07-20 21:29 WITA.
- Public UI: `https://researchos.click/`.
- Public API: `https://api.researchos.click`.
- VPS marker observed:
  `477e8bc252e47aa8d609c5cc4cb9e75e0c090799`.
- Repository resolution of the deployed abbreviated revision:
  `477e8bcc268982c7e13a5593117c48d2b48d3b59`.
- UI image:
  `researchos-ui:1d747220ddf5b30bc4cb3506adcb7f71aacdbf19`.
- PostgreSQL schema: 42.
- Canonical object count: 325.
- Monitor status: `passed`.
- API, UI, PostgreSQL, MinIO, worker, monitor, backup, and Traefik were running;
  healthchecked services were healthy.

## Reconciliation audit

The range from deployed backend revision `477e8bc` to the local candidate
contained six commits:

- three immutable production-acceptance documentation commits;
- one cross-platform restore checksum correction;
- one local operational-status projection correction; and
- one production-target registry and release-manifest commit.

The range contained no scientific review decision, ontology change, lifecycle
transition, database migration, or canonical UI source change.

The first release manifest exposed a provenance defect: the stored full marker
looked like a 40-character Git SHA but did not resolve to a repository object.
The deployment was stopped before activation. The actual commit was resolved
through Git history, correction addenda were appended to the prior acceptance
reports, and the contract test was strengthened to require the backend
revision to resolve as a Git commit.

## Candidate

- Exact source commit:
  `7879ec2259eb3f92f323008337050bd788ceede8`.
- Archive:
  `researchos-7879ec2.tar.gz`.
- Archive SHA-256:
  `ad97e9ae1e79dbdf1b3aa4961421dbfbc8f2a4575a8d33b9c958904e1a78a3c5`.
- Targeted production-registry tests: 3 passed.
- Full backend regression: 525 passed.

## Deployment

The exact archive checksum matched locally and on the VPS. Before activation,
an exact rollback archive for commit
`477e8bcc268982c7e13a5593117c48d2b48d3b59` was stored root-only at:

`/opt/researchos/deploy-backups/researchos-source-477e8bc.tar.gz`

Rollback archive SHA-256:
`b90a4756ec4814df06208baadd9c8c59450ca59954c3bd3f604383d8286b4d04`.

Only the API, worker, and monitor images and containers were rebuilt or
recreated. The UI, PostgreSQL, MinIO, backup, and Traefik containers were not
recreated.

## After state

- VPS deployed marker:
  `7879ec2259eb3f92f323008337050bd788ceede8`.
- API image:
  `sha256:88b34c01b5a1a53b122bc7676302c0b1d4662640a33892fae4e8497c9431df63`.
- Worker image:
  `sha256:1967894c777b4ce5ab159aef71fde5ca7a7d671facefda9346a912593eee767c`.
- Monitor image:
  `sha256:d51a040e7a79a9b0466a53bd17359e1f3a2313aeb480c73cff1437cc9c0aafa4`.
- UI image remained:
  `sha256:6e1320426f02a21b8df428884217cbd7ec1255f2978e73cb9f1240f5bdb842a3`.
- API and monitor: healthy.
- Worker: running.
- Monitor report: passed.
- PostgreSQL schema: 42.
- Canonical object count: 325.
- Previously accepted artifact
  `bada8f58-839b-45a1-8dde-1cf56f975841` remained in `review`.
- Public UI: HTTP 200 with HSTS.
- Public API health: `ok`.
- Browser verification displayed the canonical ResearchOS login surface with
  status `Belum masuk`.

## Failed observations preserved

1. The historical full marker did not resolve to Git, although its abbreviated
   prefix identified the correct commit.
2. During deployment, an operator-entered full candidate marker again used an
   incorrect manually expanded suffix. The source archive itself remained
   correct. The marker was corrected immediately to the exact output of local
   `git rev-parse HEAD` before acceptance.

Future deployment tooling must derive and transmit the full revision
programmatically. A manually expanded or typed SHA must not be accepted as
revision evidence.

## Decision

Source reconciliation, service health, public reachability, schema
persistence, canonical-object persistence, and rollback preservation:
**TECHNICAL ACCEPTANCE PASSED**.

At the time of technical acceptance, authenticated visual confirmation after
sign-in and refresh was pending. It was subsequently completed as recorded
below. No new scientific or database mutation was required for this
source-only reconciliation.

## Final authenticated visual confirmation

The user signed in to `https://researchos.click`, refreshed the production
workspace, and confirmed that it remained operational after refresh.

Final acceptance state: **ACCEPTED**.

This confirmation closes the visual persistence gate for the source
reconciliation. It does not record or authorize a new scientific or database
mutation.

## Source-ledger backup and remote boundary

After the deployment evidence was committed as `1171187`, a complete Git
bundle was created and verified:

- bundle: `researchos-ledger-1171187.bundle`;
- SHA-256:
  `13be9b49dcd618e06c54aa45514c86c1e42aca29dc71239517b077eb659591c0`;
- size: 1,389,362 bytes;
- off-machine location:
  `/opt/researchos/deploy-backups/researchos-ledger-1171187.bundle`;
- VPS permissions: `0600`, owner `root:root`; and
- bundle verification: complete history, passed.

Ignored environment files, runtime credentials, and private restore keys were
not tracked and therefore were not included. The tracked Ed25519 PEM is the
public restore-trust key.

The former GitHub remote was retained only as historical configuration and
renamed from `origin` to `legacy-github`. The active local branch no longer has
an upstream. No commit was pushed to GitHub during this reconciliation.
