# ResearchOS Local Stack

The local deployment is defined in `deploy/compose.yaml` and binds public
development interfaces to loopback only.

## Services

- ResearchOS API: `http://127.0.0.1:8080`
- PostgreSQL 17 with pgvector 0.8.2: `127.0.0.1:5432`
- MinIO S3 API: `http://127.0.0.1:9000`
- MinIO Console: `http://127.0.0.1:9101`
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

Port 8080 is used because port 8000 was already occupied on the installation
host. Port 9101 is used because Windows reserves port 9001.

## Operations

For a new checkout, run the secure idempotent bootstrap from the repository
root:

```powershell
py -3.13 Scripts\bootstrap_local.py
```

The command generates the three ignored credential files, starts the stack,
creates the `discoverer`, `auditor`, `reviewer`, `indexer`, `publisher`, and
`admin` browser accounts, and verifies both account login and canonical MinIO buckets. Complete
existing configuration is reused. A partial configuration fails closed instead
of guessing or overwriting credentials. Existing ResearchOS volumes without
their ignored credential files are also rejected; restore the credential files
rather than generating incompatible passwords for persisted data.

Bootstrap succeeds only after the live `/ready` contract confirms
authentication, PostgreSQL, schema version, worker heartbeat, object storage,
and local persistence paths, and after `/workspace` renders its login
interface. Use the same controller for routine operation:

```powershell
py -3.13 Scripts\bootstrap_local.py --status
py -3.13 Scripts\bootstrap_local.py --stop
```

`--status` is read-only and fails when credentials are incomplete, services
are stopped, a runtime dependency is unavailable, or the workspace cannot be
rendered. `--stop` performs a normal Compose shutdown and preserves volumes
and ignored credential files.

Verify continuity across a routine restart from the repository root:

```powershell
py -3.13 Scripts\verify_local_continuity.py
```

The verifier compares the PostgreSQL system identity, migration version, and
hashed workspace-account inventory before and after restart. It also writes,
retrieves, verifies, and removes a random MinIO sentinel. Its ignored JSON
report contains hashes and counts only; credentials and sentinel content are
not recorded.

Run commands from `deploy` and always supply the untracked local environment:

```powershell
docker compose --env-file stack.env -f compose.yaml ps
docker compose --env-file stack.env -f compose.yaml logs --tail 100
docker compose --env-file stack.env -f compose.yaml up -d
docker compose --env-file stack.env -f compose.yaml down
```

Do not use `down --volumes` unless permanent deletion of databases, objects,
monitoring history, and backups is explicitly intended.

## Persistence and backup

Docker-managed volumes store PostgreSQL, MinIO, ResearchOS knowledge artifacts,
Prometheus, Grafana, and backups. The backup process creates a PostgreSQL custom
format dump plus compressed MinIO and knowledge snapshots at startup and every
24 hours. MinIO objects are copied through the S3 API; the backup is accepted
only when recursive object metadata before and after the copy matches. The
MinIO archive includes a JSONL restoration manifest containing object metadata.
Every artifact has a verified SHA-256 sidecar, and files are published atomically after verification.
Backups are retained for 14 days by default. Configure intervals in `stack.env`.

Schema 29 adds a portable backup-set manifest that binds the PostgreSQL dump,
MinIO archive, and knowledge archive to their exact filenames and SHA-256
hashes. The manifest itself is hashed, and that hash is stored with the backup
ledger entry. A completed archive-integrity check is deliberately distinct from
recovery readiness: ResearchOS may report `backup_integrity_ready` only for a
manifest-bound set, and may report `recovery_ready` only when a matching
append-only `backup_restore_verifications` record proves a successful restore
to an isolated target. The older `ready` API field remains temporarily as a
compatibility alias for legacy archive checks and must not be interpreted as
restore evidence.

This increment defines the portable set and restore-evidence contracts only. It
does not introduce a restore executor and cannot restore over active ResearchOS
data. A later, separately reviewed increment must implement the isolated
restore drill before recovery readiness can become true.

Phase 1B adds the versioned recovery matrix at
`deploy/backup/recovery-coverage-v1.json` and the report-only verifier at
`deploy/verify/recovery_coverage.py`. The verifier checks the matrix and
manifest identities, component set, artifact paths, SHA-256 hashes, isolated
targets, and secret policy. It never performs a restore and returns
`INCOMPLETE` while any required component is partial or missing.

Run it against a locally accessible backup set with:

```powershell
python deploy/verify/recovery_coverage.py `
  --matrix deploy/backup/recovery-coverage-v1.json `
  --manifest <backup-directory>/backup-set-<stamp>.json `
  --backup-root <backup-directory> `
  --output <temporary-directory>/recovery-coverage-report.json
```

The optional `--require-complete` flag returns exit code 2 for an incomplete
matrix. It is intended for a future release gate after all six components are
implemented; it is not enabled as a passing claim during Phase 1B.

Phase 1C completes backup coverage by adding architecture, configuration, and
migration archives to every new backup set. Knowledge, architecture,
configuration, and migration use a bounded three-attempt stable-tree snapshot:
symbolic links are rejected, source manifests before and after the copy must
match, and the accepted tree manifest is stored inside the archive.

Configuration backup is allowlisted through explicit read-only mounts and
contains only `compose.yaml`, `stack.env.example`, and
`recovery-coverage-v1.json`. The real `stack.env`, local access credentials,
passwords, and tokens are never mounted into the snapshot source. Migration
backup contains the migration runner and the versioned SQL directory.

A `COMPLETE` recovery coverage report now means only that all six artifacts are
present, hash-verified, and ready for an isolated restore drill. It does not
mean a restore occurred, does not write restore evidence, and does not make
`recovery_ready` true.

Phase 1D adds a manually invoked restore drill in
`deploy/restore/compose.restore-drill.yaml`. It is deliberately separate from
the normal stack: its network is internal, its PostgreSQL and MinIO data live
only on `tmpfs`, the backup volume is read-only, and neither the active
PostgreSQL database nor the active MinIO service is addressable from the drill
executor. Database and bucket names are constants owned by the executor rather
than operator-provided targets.

Run one drill from `deploy/restore`:

```powershell
$env:RESTORE_MANIFEST = "backup-set-YYYYMMDDTHHMMSSZ.json"
$env:RESTORE_REPORT_DIR = (Resolve-Path "..\..\.tmp").Path
$env:RESTORE_REPORT = "restore-drill-report.json"
docker compose -f compose.restore-drill.yaml --profile restore-drill up `
  --build --abort-on-container-exit --exit-code-from restore-drill
docker compose -f compose.restore-drill.yaml --profile restore-drill down `
  --remove-orphans
```

The executor revalidates the six-component manifest, safely extracts archives
without links or traversal, verifies filesystem tree manifests, restores and
checks the migration ledger in PostgreSQL, restores MinIO objects and compares
their sizes and SHA-256 content, validates the non-secret configuration
allowlist, and then removes the temporary database and bucket. The resulting
JSON is attributable and content-hashed. It has `ledger_written: false`;
therefore even a `verified` Phase 1D report does not make the operational
`recovery_ready` projection true. Ledger admission belongs to a separately
accepted increment.

Phase 1E adds signed restore-evidence admission. A restore report can affect
`recovery_ready` only after the isolated drill signs the canonical report with
an Ed25519 private key, the admission command verifies its signature and
invariants, PostgreSQL admits it through the schema 30 admission function, and
the recovery projection revalidates it against the live trust registry.

Generate the local signing key once from the repository root:

```powershell
AI-Gateway\.venv\Scripts\python.exe `
  deploy\restore\bootstrap_attestation_key.py
```

The private key is written below `deploy/restore/private/` and must never be
committed, copied into a report, mounted into the API, or mounted into the
admission service. Only the public key and
`deploy/restore/trust/trusted-restore-keys.json` belong in source control.

Run the signed drill using the Phase 1D command above. Its report is written
below the ignored `deploy/restore/reports/` directory by default. Admit a
verified report from `deploy` with:

```powershell
$env:RESTORE_REPORT_PATH = "/restore-reports/restore-drill-report.json"
docker compose --env-file stack.env -f compose.yaml --profile restore-admission `
  run --rm restore-admission
```

Admission is idempotent by report content hash. Tampered reports, unknown or
revoked keys, partial component sets, mutable target claims, failed cleanup,
and mismatched backup manifests fail closed. The admission service receives
only the selected report, public trust material, and database access. It has no
private signing key, backup volume, active storage target, API route, worker,
or scheduler.

To revoke a signing key, change its registry status from `active` to `revoked`
and deploy the updated public trust registry. Live recovery projection then
withdraws trust from previously admitted evidence signed by that key. Generate
a new key with a new private-key filename for rotation; the bootstrap command
preserves existing registry entries and appends the new key. Never overwrite or
reuse the old private key.

Phase 1F-A adds a live freshness gate without introducing a scheduler.
`restore_verified` continues to mean that the matching evidence is
cryptographically valid and currently trusted. `restore_fresh` separately
means its completion time is no older than
`RESTORE_EVIDENCE_MAX_AGE_SECONDS` and is not farther into the future than
`RESTORE_EVIDENCE_CLOCK_SKEW_SECONDS`. Operational `recovery_ready` requires
both values plus portable backup integrity.

The defaults are seven days and five minutes respectively:

```dotenv
RESTORE_EVIDENCE_MAX_AGE_SECONDS=604800
RESTORE_EVIDENCE_CLOCK_SKEW_SECONDS=300
```

Evidence at the exact maximum-age boundary remains fresh. Evidence beyond that
boundary or beyond the allowed future clock skew fails closed with an explicit
reason. Changing the configured maximum age affects the live projection only;
it never mutates or deletes the immutable signed evidence.

Phase 1F-B adds Schema 31 exclusive restore-drill coordination. It does not
schedule or execute a drill. PostgreSQL selects the latest eligible canonical
backup, issues one bounded lease, and returns only its exact backup identity and
safe manifest filename. A second acquisition is rejected while that lease is
active. Expired leases are failed explicitly before a later run may begin.

Acquire a one-hour lease from `deploy`:

```powershell
docker compose --env-file stack.env -f compose.yaml `
  --profile restore-coordinator run --rm restore-coordinator `
  acquire --owner manual-controller --lease-seconds 3600
```

Keep the returned `run_id` and `lease_token` only in the invoking process.
After the isolated drill and Phase 1E admission succeed, complete the run:

```powershell
docker compose --env-file stack.env -f compose.yaml `
  --profile restore-coordinator run --rm restore-coordinator `
  complete --run-id <run-id> --lease-token <lease-token> `
  --report-content-hash <content-hash> `
  --verification-id <verification-id> --actor manual-controller
```

If any step fails, close the lease with an explicit reason:

```powershell
docker compose --env-file stack.env -f compose.yaml `
  --profile restore-coordinator run --rm restore-coordinator `
  fail --run-id <run-id> --lease-token <lease-token> `
  --error "<explicit failure reason>" --actor manual-controller
```

The coordinator mounts only its command and receives only PostgreSQL access.
It has no private key, backup volume, report volume, trust registry, Docker
socket, API route, worker job, or active-storage target. The drill still has no
database credential, and admission remains the only path to canonical restore
evidence.

Phase 1F-C adds a manually invoked host controller for the complete accepted
workflow. Run it from the repository root:

```powershell
AI-Gateway\.venv\Scripts\python.exe `
  deploy\restore\run_restore_drill_controller.py `
  --owner "<operator identity>" --lease-seconds 7200
```

The controller accepts only an attributable owner and bounded lease duration.
PostgreSQL selects the backup. The controller then runs the fixed isolated
drill, always attempts Compose teardown, admits the signed report through the
public-trust boundary, and completes the lease with the exact canonical
verification ID and content hash. Any failure after acquisition attempts to
close the lease with an explicit stage reason.

Reports are retained below the ignored
`deploy/restore/reports/<run-id>/` directory. The controller does not accept
backup paths, target identifiers, report paths, database URLs, or key paths.
It is not a scheduler and is not exposed through the API, UI, or worker.

Phase 1F-D adds a canonical schedule that starts paused. Inspect it from
`deploy`:

```powershell
docker compose --env-file stack.env -f compose.yaml `
  --profile restore-coordinator run --rm restore-coordinator schedule-status
```

Configure a bounded cadence, then activate it with separate attributable
decisions:

```powershell
docker compose --env-file stack.env -f compose.yaml `
  --profile restore-coordinator run --rm restore-coordinator `
  schedule-configure --cadence-seconds 604800 `
  --actor "<operator identity>" --rationale "<reason>"

docker compose --env-file stack.env -f compose.yaml `
  --profile restore-coordinator run --rm restore-coordinator `
  schedule-resume --actor "<operator identity>" --rationale "<reason>"
```

A host scheduler may invoke the controller frequently; PostgreSQL decides
whether work is due:

```powershell
AI-Gateway\.venv\Scripts\python.exe `
  deploy\restore\run_restore_drill_controller.py `
  --owner "<host trigger identity>" --lease-seconds 7200 --scheduled
```

`paused`, `not_due`, and an already-running slot are successful no-op
decisions. The host cannot provide a due time, backup, target, report, or key.
To pause future slots, use `schedule-pause` with actor and rationale. An active
slot must finish or fail before schedule configuration or status can change.

Phase 1F-E provides a Windows Task Scheduler contract. Previewing it changes
nothing:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File Scripts\restore_drill_task.ps1 -Action Plan
```

Inspect installation status without mutation:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File Scripts\restore_drill_task.ps1 -Action Status
```

Installation is an explicit later operation:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File Scripts\restore_drill_task.ps1 -Action Install
```

The installed task is disabled. It runs only as the current interactive user
with limited privilege, ignores overlapping triggers, and invokes the
controller hourly in `--scheduled` mode. Enabling the task and resuming the
database schedule are separate decisions.

Removal also requires explicit confirmation:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass `
  -File Scripts\restore_drill_task.ps1 `
  -Action Remove -ConfirmRemoval
```

Removing the Windows task does not remove PostgreSQL schedule policy, audit
events, reports, or restore evidence.

## Database migrations

PostgreSQL schema changes are applied by the one-shot `migrate` service before
the API, worker, or backup service starts. Every migration is recorded in
`schema_migrations` with its version, filename, and SHA-256 checksum. A changed
checksum or incomplete legacy baseline stops deployment instead of guessing.

For an existing volume, apply and verify pending migrations with:

```powershell
docker compose --env-file stack.env -f compose.yaml run --rm migrate
```

The command is idempotent. The API also checks `DATABASE_SCHEMA_VERSION` during
startup and refuses to run against an older or newer schema. Never edit a
migration that has already been applied; add a new numbered migration instead.

## Background jobs

Workers claim jobs using `FOR UPDATE SKIP LOCKED`. Supported job types are
`normalize_metadata`, `index_embedding`, and `parse_document`. Job status,
attempts, errors, and timestamps remain inspectable in `background_jobs`.
Claims carry a bounded lease so interrupted `running` jobs return to the queue.
Failures use exponential backoff and move to `dead_letter` after
`JOB_MAX_ATTEMPTS`; worker shutdown waits for the active job boundary. Configure
the attempt limit, lease duration, and retry base through `stack.env`.
Each job runs in an isolated child process with a hard timeout configured by
`JOB_TIMEOUT_SECONDS`; timed-out processes are terminated before retry handling.
The configured lease must be longer than the hard timeout so another worker
cannot reclaim a job while its isolated process is still active.
The current HNSW embedding index uses 1536 dimensions; workers reject vectors
with a different shape instead of silently storing incompatible embeddings.
Every embedding job must also provide a canonical object UUID and source
content hash.
The vector table is a derived retrieval index. Canonical identity and storage
responsibilities are defined in `SCIENTIFIC_DATA_STORAGE.md`.

Discovery and metadata collection now write to the canonical PostgreSQL model
when `DATABASE_URL` is configured. Run the repeatable acceptance check inside
the API runtime with:

```powershell
docker cp verify\canonical_repository.py researchos-api-1:/tmp/canonical_repository.py
docker compose --env-file stack.env exec -T api python /tmp/canonical_repository.py
```

The check deliberately runs twice and verifies canonical deduplication,
immutable observations, and metadata-version idempotency.

Acquired PDFs are additionally stored in the `researchos-documents` MinIO
bucket using content-addressed keys. PostgreSQL stores their canonical object,
checksum, size, media type, retrieval provenance, and monotonically allocated
document version. Verify both stores together with:

```powershell
docker cp verify\representation_repository.py researchos-api-1:/tmp/representation_repository.py
docker compose --env-file stack.env exec -T api python /tmp/representation_repository.py
```

This acceptance check also reads the object back and confirms that a checksum
mismatch and a missing object are both rejected. With MinIO configured, the
evidence extraction path uses only a successfully verified object payload;
the local filesystem registry remains a compatibility fallback for deployments
without object storage.

Canonical evidence persistence can be checked after the canonical repository
and representation checks with:

```powershell
docker cp verify\canonical_evidence.py researchos-api-1:/tmp/canonical_evidence.py
docker compose --env-file stack.env exec -T api python /tmp/canonical_evidence.py
```

The check verifies exact representation linkage, coordinates, parser version,
initial `pending` review state, idempotency, and rollback on an evidence
identity/content conflict.

Evidence review requires a separate principal with the `reviewer` role in
`KNOWLEDGE_API_PRINCIPALS`. Reviewer identity is derived from its Bearer token
and cannot be supplied or overridden in the request body. The canonical
evidence acceptance check also verifies idempotent retries, superseding review
history, provenance linkage, and append-only enforcement.

Canonical graph persistence requires every included evidence object to be
accepted first. Run the graph acceptance check after the canonical evidence
check:

```powershell
docker cp verify\canonical_graph.py researchos-api-1:/tmp/canonical_graph.py
docker compose --env-file stack.env exec -T api python /tmp/canonical_graph.py
```

It verifies reviewed node linkage, edge provenance, reviewer attribution,
idempotency, fail-closed rejection of unaccepted evidence, and selective edge
invalidation after a later evidence rejection.

Artifact lifecycle transitions use
`POST /knowledge/artifacts/{artifact_id}/transitions` and require a principal
with the `reviewer` role. The request supplies `to_status`, `rationale`, and
`occurred_at`; actor identity is always derived from the Bearer token. Verify
artifact creation, strict transitions, retry idempotency, and append-only
history with:

```powershell
docker cp verify\canonical_artifacts.py researchos-api-1:/tmp/canonical_artifacts.py
docker compose --env-file stack.env exec -T api python /tmp/canonical_artifacts.py
```

Published Markdown is stored in the `researchos-documents` bucket under the
content-addressed `publications/` namespace. Verify multiple edition versions,
idempotent retries, read-back integrity, and database immutability with:

```powershell
docker cp verify\canonical_publications.py researchos-api-1:/tmp/canonical_publications.py
docker compose --env-file stack.env exec -T api python /tmp/canonical_publications.py
```

Semantic indexing requires an `indexer` principal. Submit exactly 1536 vector
dimensions to `POST /knowledge/semantic-index/jobs`; the API and worker both
revalidate canonical eligibility and content hash. Verify accepted evidence,
validated artifacts, duplicate job suppression, stale-job rejection, and full
derived-index rebuild with:

```powershell
docker cp verify\canonical_semantic_index.py researchos-api-1:/tmp/canonical_semantic_index.py
docker compose --env-file stack.env exec -T api python /tmp/canonical_semantic_index.py
```

Semantic retrieval uses `POST /knowledge/semantic-search`. It returns canonical
identity and provenance rather than raw vectors. Eligibility is evaluated from
the current evidence review and artifact lifecycle state on every query, so
rejected evidence, deprecated artifacts, and stale content hashes cannot appear
even when historical vector rows remain present.

Run the final cross-store compliance scan with:

```powershell
docker cp verify\storage_compliance.py researchos-api-1:/tmp/storage_compliance.py
docker compose --env-file stack.env exec -T api python /tmp/storage_compliance.py
```

Backup restore verification must always target an isolated temporary database;
never restore over the active `researchos` database. The latest verified result
and staging-retirement decisions are documented in
`STORAGE_COMPLIANCE_REPORT.md`.

## Worker monitoring

The worker exposes Prometheus metrics only on the internal Compose network at
`worker:9102/metrics`. Metrics cover database heartbeat time, queue depth by
status, job outcomes by type, and job duration count/sum. Prometheus loads four
alerts from `deploy/monitoring/worker-alerts.yml`: unavailable metrics, stale
database heartbeat, dead-letter jobs, and sustained pending queue backlog. Use
the Prometheus **Status > Targets** and **Alerts** pages to inspect current state.

## Security

Local secrets are stored in ignored `deploy/stack.env`. Services bind only to
`127.0.0.1`. Prometheus uses a dedicated ignored auditor token to scrape the
protected ResearchOS metrics endpoint.
