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
format dump plus compressed MinIO and knowledge-volume snapshots at startup and
every 24 hours. It verifies every archive and retains 14 days by default.
Configure intervals in `stack.env`.

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

## Security

Local secrets are stored in ignored `deploy/stack.env`. Services bind only to
`127.0.0.1`. Prometheus uses a dedicated ignored auditor token to scrape the
protected ResearchOS metrics endpoint.
