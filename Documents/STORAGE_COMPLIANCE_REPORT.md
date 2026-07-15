# ResearchOS Storage Consolidation and Compliance Report

## Outcome

DATA-002L passed on 2026-07-16 (Asia/Makassar). The canonical scientific data
stack is internally consistent, cross-store representations are reachable, the
semantic index remains derived, and the latest backup was successfully restored
into an isolated temporary database.

## Ownership contract

PostgreSQL table `storage_contract_registry` records 21 governed resources with
an owner component, responsibility, source-of-truth designation, lifecycle
class, active state, and operational notes. The
`storage_contract_compliance` view reports database resource presence.

Responsibility boundaries are:

- canonical identity, state, evidence, graph, and artifacts: PostgreSQL;
- immutable document and publication bytes: MinIO;
- semantic similarity: derived pgvector index;
- execution coordination: PostgreSQL background job queue;
- portable run snapshots and extraction compatibility: knowledge filesystem;
- audit and attributable transitions: append-only PostgreSQL ledgers.

## Staging disposition

- PostgreSQL `document_registry` is retired and inactive. No application code
  uses it. It is preserved temporarily for migration audit rather than dropped.
- Filesystem `DocumentRegistry` remains active only as an extraction
  compatibility interface and is not canonical when PostgreSQL and MinIO are
  configured.
- `normalized_metadata` remains active operational staging because the
  `normalize_metadata` worker still writes it. Canonical metadata lives in
  `scientific_documents` and `metadata_observations`.
- `background_jobs` remains an active operational queue and rebuild input.
- `embedding_index` is explicitly classified as derived and rebuildable.

## Automated compliance evidence

`deploy/verify/storage_compliance.py` passed with:

- 21 registered storage contracts;
- all registered PostgreSQL resources present;
- zero orphan canonical documents, representations, evidence, graph edges,
  artifact lifecycle events, or publication editions;
- all required immutability triggers present;
- HNSW cosine index present;
- all embeddings using 1536 dimensions;
- both governed MinIO buckets reachable;
- four canonical representations verified against MinIO size, media type, and
  SHA-256 metadata.

## Backup restoration evidence

Backup `researchos-20260715T163834Z.dump` was restored with `pg_restore` into
temporary database `researchos_restore_check`. The restored database contained:

- 21 storage contracts;
- 13 canonical objects;
- 35 provenance events.

The temporary database was dropped after verification. The active `researchos`
database was never overwritten or modified by the restore test.

## Architecture and regression evidence

Architecture Engine scanned 253 Python files and produced 627 nodes and 1,372
edges with graph hash
`c9781488a91a058048e76830b4efd30d53b746f2905e0403d74a41651db9ff6b`.

The complete automated regression suite passed: 119 tests, with one upstream
Starlette deprecation warning and no test failures.

## Residual work

The retired PostgreSQL `document_registry` table may be physically removed only
after a separately approved retention window. The filesystem extraction
compatibility registry and `normalized_metadata` staging table should be retired
only after their remaining worker and extraction consumers are migrated.
