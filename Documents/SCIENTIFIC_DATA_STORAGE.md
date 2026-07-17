# Scientific Data Storage Architecture

## Decision

ResearchOS stores scientific objects, not merely files or database rows.
Technology selection follows canonical identity, lifecycle, representation,
provenance, and relationship design.

The storage responsibility model is:

```text
Canonical scientific identity and state -> PostgreSQL
Physical representations                -> MinIO / object storage
Scientific relationships                -> PostgreSQL adjacency tables
Semantic retrieval                      -> pgvector derived index
Audit and provenance                    -> append-only PostgreSQL ledger
```

Files and vectors are representations or indexes. Neither is the identity or
source of truth of a scientific object.

## Identity–representation separation

`canonical_objects` owns stable identity, lifecycle, classification, and
version. `scientific_representations` records physical PDF, HTML, XML, JSON,
dataset, and publication formats using storage URI, checksum, media type, size,
version, source, and retrieval method.

One scientific document can therefore have many representations and versions
without changing its canonical identity. Content changes create a new
representation; old content is never silently overwritten.

## Storage layers

1. Source registry stores provider-specific identity and immutable response
   hashes.
2. Canonical metadata maps multiple provider records to one scientific
   document while retaining every observation and match decision.
3. Representation repository stores only object-storage references and
   integrity metadata in PostgreSQL; bytes live in MinIO.
4. Evidence repository stores typed scientific units with exact source
   coordinates and review state.
5. Provenance ledger connects workflow, task, context, agent, provider, model,
   configuration, source/output objects, and human reviewer. Ledger events are
   append-only.
6. Knowledge store uses PostgreSQL adjacency tables behind a graph abstraction.
   A separate graph database is not justified until measured traversal needs
   require it.
7. Semantic retrieval uses pgvector as a derived, rebuildable index that always
   references a canonical object and content hash.
8. Artifact and publication repositories separate canonical research outputs,
   lifecycle events, and their Markdown/PDF/DOCX/HTML/JSON/CSV/RDF editions.

## Lifecycle

Canonical lifecycle states are:

```text
planned -> draft -> review -> validated -> ratified -> published
                                                -> deprecated -> archived
```

Transitions for official artifacts are recorded as attributable lifecycle
events; changing a file does not change lifecycle state.

## Evolution roadmap

| Sprint | Focus | Initial implementation |
|---|---|---|
| DATA-001A | Canonical identity and schema | Python models + PostgreSQL contract |
| DATA-001B | Source registry and metadata | PostgreSQL |
| DATA-001C | Raw representations | MinIO + representation records |
| DATA-001D | Checksum, version, integrity | PostgreSQL + SHA-256 |
| DATA-001E | Evidence and claims | PostgreSQL |
| DATA-001F | Provenance ledger | Append-only PostgreSQL events |
| DATA-001G | Artifact repository and lifecycle | PostgreSQL |
| DATA-001H | Knowledge relationships | PostgreSQL adjacency tables |
| DATA-001I | Semantic retrieval | pgvector |
| DATA-001J | Publication repository | PostgreSQL identity + MinIO bytes |
| DATA-001K | Backup, migration, retention | Database and object backups |
| DATA-001L | Consolidation and compliance | Architecture Engine review |
| DATA-002A | Repository contracts and transaction boundary | Python protocol + PostgreSQL adapter |
| DATA-002B | Source and metadata persistence | Canonical transactional persistence |
| DATA-002C | Representation repository | MinIO bytes + PostgreSQL identity/version |
| DATA-002D | Representation integrity and retrieval | Verified MinIO reads before parsing |
| DATA-002E | Canonical evidence persistence | Transactional evidence + exact source coordinates |
| DATA-002F | Evidence human review workflow | Attributed decisions + append-only provenance |
| DATA-002G | Canonical knowledge graph persistence | Reviewed nodes + provenance-required edges |
| DATA-002H | Canonical artifact and lifecycle repository | Attributed state machine + immutable history |
| DATA-002I | Canonical publication representations | Content-addressed immutable editions |
| DATA-002J | Canonical semantic indexing | Eligibility-gated rebuildable pgvector index |
| DATA-002K | Canonical semantic retrieval | Current-state filtering + provenance-bearing hits |
| DATA-002L | Storage consolidation and compliance | Ownership registry + restore verification |
| PRODUCT-001A | Object-centric product read model | Projects, paginated objects, unified detail, permissions |

## Current implementation status

Migration `003_canonical_scientific_data.sql` establishes the complete storage
contract and keeps earlier operational tables as staging interfaces.
DATA-002A/B are now implemented: the Scientific Knowledge service persists
discovery and normalized metadata through a repository protocol and one
PostgreSQL transaction per run. DOI is preferred as the canonical stable key;
an internal literature record ID is used when DOI is unavailable. Provider
sources, match decisions, raw observations, and normalized observations remain
individually traceable and idempotent by content hash.

Filesystem manifests remain a supported fallback when `DATABASE_URL` is not
configured and remain useful as portable run snapshots. They must not be
deleted during the transition. The repeatable stack acceptance check is
`deploy/verify/canonical_repository.py`.

DATA-002C stores acquired PDF bytes under a SHA-256 content-addressed MinIO
key and records the durable `s3://` URI in `scientific_representations`.
Representation versions are allocated per canonical object and format while
identical checksums are idempotent. The adapter verifies that acquisition
provenance belongs to the exact canonical discovery record before linking it.
The filesystem registry remains available to the existing extraction pipeline
until representation-backed extraction is introduced. The repeatable
acceptance check is `deploy/verify/representation_repository.py`.

DATA-002D makes object storage the extraction read path whenever MinIO is
configured. Retrieval resolves the exact representation by canonical identity
and source-document checksum, then validates the configured bucket, object
size, media type, stored checksum metadata, payload length, and payload
SHA-256 before parsing. Missing or inconsistent objects fail closed and do not
produce extraction manifests. Filesystem reads occur only when object storage
is not configured.

DATA-002E persists extracted claims, methods, variables, datasets, results,
limitations, and conclusions as canonical evidence objects. Each row retains
the canonical document and exact representation, statement, page and character
coordinates, parser name/version, extraction confidence, quote hash, and human
review status. A complete extraction is committed in one transaction;
repeated deterministic objects are idempotent and identity/content conflicts
fail closed. New machine-extracted objects begin with human review status
`pending`. The repeatable acceptance check is
`deploy/verify/canonical_evidence.py`.

DATA-002F exposes `POST /knowledge/evidence/{object_id}/reviews` to principals
with the dedicated `reviewer` role. The reviewer identity comes exclusively
from the authenticated principal; clients provide only decision, rationale,
and occurrence time. Each accepted or rejected decision updates the current
evidence review state while atomically appending an immutable review event and
an immutable provenance event. Identical retries are idempotent, superseding
decisions retain the complete prior history, and database triggers reject
updates or deletion of ledger records. Migration
`004_evidence_review_workflow.sql` adds the review ledger.

DATA-002G persists graph nodes and assertions into PostgreSQL adjacency tables.
The adapter revalidates every evidence object against canonical database state
and accepts only evidence whose current human review status is `accepted` and
whose statement, type, and quote hash match the graph snapshot. Every edge has
an immutable provenance event containing its graph identity, relationship,
supporting evidence, accepted-review provenance, and attributed reviewer.
Identical graph persistence is idempotent. If accepted evidence is later
rejected, dependent edges are retained for audit but their review status is
changed to `rejected`; unrelated edges remain accepted. Migration
`005_canonical_knowledge_graph.sql` aligns the relationship constraint with the
domain graph. The repeatable acceptance check is
`deploy/verify/canonical_graph.py`.

DATA-002H stores theory bundles, gap analyses, validation reports, and
publication packages as canonical research artifacts with their complete
domain metadata. Creation is an attributable lifecycle event with immutable
provenance. Subsequent transitions use the strict state machine
`planned -> draft -> review -> validated -> ratified -> published -> deprecated
-> archived`; skipping states is rejected. Reviewer identity comes from the
authenticated principal, rationale is mandatory, identical retries are
idempotent, and both lifecycle and provenance ledgers are append-only.
Validation reports begin at `validated`, publication packages at `published`,
and theory/gap artifacts at `draft`. Migration `006_artifact_lifecycle.sql`
enforces lifecycle ledger uniqueness and immutability. The repeatable
acceptance check is `deploy/verify/canonical_artifacts.py`.

DATA-002I stores publication Markdown as SHA-256 content-addressed objects in
MinIO and links each edition to its published canonical artifact through
`scientific_representations` and `publication_representations`. PostgreSQL
records storage URI, media type, byte size, checksum, monotonically allocated
format version, edition type, publication time, and a deterministic publication
hash. Identical publication retries are idempotent; changed content creates a
new version and edition record. Retrieval revalidates MinIO metadata, size,
media type, and payload SHA-256. Migration
`007_immutable_publication_representations.sql` makes both scientific and
publication representation records immutable. The acceptance check is
`deploy/verify/canonical_publications.py`.

DATA-002J provides `POST /knowledge/semantic-index/jobs` for principals with
the dedicated `indexer` role. Evidence is eligible only while its canonical
human review status is `accepted`; artifacts are eligible only in `validated`,
`ratified`, or `published` lifecycle states. Eligibility, canonical identity,
and content hash are validated both when the job is enqueued and again by the
worker. Embeddings require exactly 1536 dimensions. Job deduplication uses
canonical object, content hash, and model; vector uniqueness uses the same
identity, allowing changed content to create a new derived entry without
overwriting history. Migration `008_canonical_semantic_index.sql` establishes
these constraints. The index remains disposable and rebuildable from canonical
job payloads; it never becomes a source of scientific truth. The acceptance
check is `deploy/verify/canonical_semantic_index.py`.

DATA-002K provides `POST /knowledge/semantic-search` for authenticated
discoverers. Queries require the embedding model, exactly 1536 query
dimensions, a bounded result limit, and explicit evidence/artifact filters.
Similarity is computed with pgvector cosine distance, but eligibility is joined
against current canonical state at query time: evidence must still be accepted
with the same content hash, and artifacts must still be validated, ratified,
or published with the same canonical metadata hash. Rejected, deprecated, or
stale objects disappear immediately without deleting historical vectors.
Responses expose canonical identity, similarity, content hash, safe metadata,
and review/lifecycle provenance with attributed actor; raw vectors are never
returned. Migration `009_semantic_retrieval.sql` adds stable canonical artifact
content hashes and retrieval eligibility indexing. The semantic acceptance
check also covers retrieval invalidation.

DATA-002L closes the storage implementation increment with a governed registry
of 21 PostgreSQL, MinIO, filesystem, queue, and derived-index resources. Each
resource has an explicit owner, responsibility, source-of-truth designation,
lifecycle class, and active/retired state. The unused PostgreSQL
`document_registry` staging table is marked retired but retained for migration
audit; `normalized_metadata` and the filesystem registry remain explicitly
temporary because active consumers still exist. Cross-store compliance,
immutability triggers, referential integrity, HNSW presence, dimensions, bucket
availability, and representation integrity are checked by
`deploy/verify/storage_compliance.py`. Migration
`010_storage_contract_registry.sql` creates the registry and compliance view.
The complete evidence is recorded in `STORAGE_COMPLIANCE_REPORT.md`.

PRODUCT-001A adds the first object-centric product contract without changing
the canonical write workflows. Migration `011_product_read_model.sql` creates
project identity and project membership, backfills the default ResearchOS
project, and automatically assigns new canonical objects. Authenticated users
can list projects, search/filter objects with stable cursor pagination, and
open a project-scoped deep link. The unified object detail combines identity,
subtype metadata, representations, relationship neighborhood, provenance
timeline, lifecycle, and role-aware available actions. Read access accepts any
configured principal, while review, lifecycle, and semantic-index actions keep
their existing dedicated roles.

PRODUCT-001B exposes that contract as a responsive Object Workspace at
`/workspace`. The workspace provides project selection, debounced search,
canonical type filters, cursor-based loading, project/object deep links, and a
unified inspector with overview, provenance, relationships, representations,
lifecycle, and permission-aware actions. It is shipped as dependency-free
static assets inside the API image. Access tokens are never embedded in the
application or URL and are retained only in browser session storage.

PRODUCT-001C adds an operational Review Inbox backed by a project-scoped work
queue. It summarizes pending evidence reviews, actionable artifact lifecycle
transitions, semantic index jobs, and failed jobs. Reviewers receive structured
decision forms with explicit decision/target state, required rationale,
provenance confirmation, submitting/error/success states, and automatic queue
refresh. Auditors can inspect the same queue while mutation controls remain
disabled; indexers can monitor semantic jobs. The UI never fabricates an
embedding: new indexing work continues to require a valid model and exactly
1536 dimensions through the governed semantic-index API.

PRODUCT-001D adds a project-scoped interactive Scientific Relationship Graph.
The graph read API returns canonical object identity, directed edges,
confidence, review status, and provenance with a bounded maximum of 300 edges.
The workspace renders an accessible SVG neighborhood with object-type color,
direction markers, relationship labels, deterministic layout, keyboard-focusable
nodes, confidence/status/type filters, node focus details, and navigation into
the existing Object Inspector deep link. An expandable relationship list is
provided as the non-visual accessible representation; graph data remains a
projection over PostgreSQL canonical nodes and edges.

PRODUCT-001E completes the primary product loop with a Discovery & Document
Ingestion Workspace. An authenticated capability endpoint supplies provider,
limit, access-status, and workflow contracts so the client does not duplicate
backend configuration. Discoverers can define a scientific question and search
plan, select OpenAlex/Crossref/Semantic Scholar, constrain result counts and
years, inspect deduplicated records and provider failures, collect normalized
metadata, acquire a selected PDF with source-provider/response-hash provenance,
verify object integrity, and extract evidence. The four-stage UI reports
running/complete/failed state and refreshes the canonical object list after
extraction. External discovery is not run automatically; every network search
requires an explicit user submission.

PRODUCT-001F replaces manual tokens for human users with revocable workspace
sessions while retaining bearer authentication for automation. Migration
`012_workspace_sessions.sql` adds canonical users, operational sessions, and an
append-only authentication audit. Passwords use PBKDF2-SHA256 with individual
random salts and 310,000 iterations; raw passwords and session tokens are never
stored in PostgreSQL. Browser sessions use 256-bit random tokens, hashed server
side, 12-hour expiry, HttpOnly/SameSite=Strict cookies, rotation of CSRF tokens
on session recovery, and mandatory CSRF validation for cookie-authenticated
mutations and logout. Five failed attempts cause a 15-minute lock. Four local
role-separated accounts are bootstrapped, with initial credentials retained
only in the Git-ignored `deploy/local-access.env` file.

PRODUCT-001G adds an administrator-only control plane for user status, session
revocation, authentication audit, and verified backup/recovery readiness.
Research roles cannot invoke administrative actions. Backup readiness is based
on a PostgreSQL ledger written only after the database, MinIO, and knowledge
archives all pass integrity checks.

DATA maintenance Phase 1A (schema 29) corrects the recovery semantics without
breaking existing clients. Each new backup publishes a deterministic,
SHA-256-bound manifest for its PostgreSQL, MinIO, and knowledge components.
`backup_runs` remains mutable operational staging while a backup is being
constructed; it is no longer classified as an immutable ledger. Isolated
restore results belong to the separate append-only
`backup_restore_verifications` ledger. A composite foreign key binds every
verification to the exact backup ID and manifest hash, the target kind is
restricted to `isolated`, and non-empty check evidence plus actor and timing
provenance are mandatory.

The recovery projection now distinguishes legacy component checks
(`ready`, retained only as a deprecated compatibility alias), portable set
integrity (`backup_integrity_ready`), isolated restore proof
(`restore_verified`), and the conjunction required for an operational recovery
claim (`recovery_ready`). Phase 1A defines no restoration executor and performs
no mutation of active PostgreSQL, MinIO, knowledge, or architecture data.

DATA maintenance Phase 1B adds a versioned, report-only Recovery Coverage
Matrix. Its required component set is PostgreSQL, MinIO, knowledge,
architecture, configuration, and migration. The verifier binds a matrix hash
and backup manifest hash, rejects unsafe paths, symbolic links, unexpected
components, missing files, and hash mismatches, and records that neither a
restore nor an active-target mutation occurred. Configuration recovery is
limited to reconstructable structure and explicitly prohibits secret values.

The current evidence-based outcome is `INCOMPLETE`: PostgreSQL, MinIO, and
knowledge artifacts are present and hash-verified; architecture and
configuration are missing; migration coverage is partial because the database
contains its migration ledger but the backup set does not yet carry the
versioned migration files or forward-recovery evidence. This report is not a
restore result and cannot populate `backup_restore_verifications`.

DATA maintenance Phase 1C supersedes that coverage outcome for newly produced
backup sets. Architecture state, an allowlisted non-secret configuration
bundle, and the migration runner plus all versioned SQL files are now stable
filesystem snapshots alongside PostgreSQL, MinIO, and knowledge. Each
filesystem snapshot rejects symbolic links, compares source tree manifests
before and after copying, retries at most three times, and preserves the
accepted tree manifest inside its archive.

The resulting six-component matrix can report `COMPLETE`, meaning ready for an
isolated restore drill. Architecture may legitimately be an explicitly proven
empty tree. Configuration contains reconstruction structure only and never the
active environment or credential values. No restore is performed, the
`backup_restore_verifications` ledger remains unchanged, and operational
`recovery_ready` remains false until a later restore increment succeeds.

DATA maintenance Phase 1D introduces that restore operation only as a manually
invoked, isolated and report-only drill. A dedicated Compose project creates
executor-owned PostgreSQL and MinIO targets on an internal network with tmpfs
storage. The executor can read the canonical backup volume but cannot resolve,
mount, or receive identifiers for the active storage targets.

Before mutation of its temporary targets, the executor reruns recovery coverage
and hash checks. Archive extraction rejects absolute paths, traversal, links,
devices, duplicate members, and unknown member types. Knowledge, architecture,
configuration, and migration trees must match their embedded manifests.
PostgreSQL must restore successfully and its `schema_migrations` ledger must
match every archived migration file and checksum. MinIO object sizes and
content hashes must match the restored source. Configuration remains restricted
to the three-file non-secret allowlist.

The executor always attempts removal of its fixed temporary database and bucket
and reports cleanup failure as a failed drill. Its report includes actor,
timestamps, backup and manifest identity, fixed isolated target identity,
component checks, outcome, cleanup result, and a content hash. Phase 1D does
not insert that report into `backup_restore_verifications`, expose an API,
schedule execution, or assert operational recovery readiness.

DATA maintenance Phase 1E introduces the separately reviewed admission
boundary. The drill signs its canonical report with a local Ed25519 private
key. Admission verifies that signature against a versioned public trust
registry, revalidates the fixed isolated target, exact six-component evidence,
successful cleanup, backup identity, manifest binding, and content hash, and
then calls the schema 30 admission function. Replay of the same report is
idempotent by content hash.

The database guard rejects partial or structurally forged `verified` rows.
Cryptographic trust is also revalidated by the live recovery projection, so a
raw database insert, stale trust decision, revoked key, or modified report
cannot produce `recovery_ready`. The signing key is available only to the
isolated drill; the API and admission service mount public trust material only.
No admission API, UI action, worker job, or scheduler is introduced.

DATA maintenance Phase 1F-A adds freshness as another independent live
admission condition. A trusted signature remains `restore_verified`, preserving
the historical fact and its provenance, while `restore_fresh` is calculated
from the signed completion timestamp and configured maximum age. The
operational `recovery_ready` projection requires backup integrity, trusted
verification, and freshness simultaneously.

The projection also rejects completion timestamps beyond a bounded future
clock-skew allowance. Freshness policy changes do not rewrite the append-only
restore ledger. This increment does not schedule a drill, add an orchestration
service, or grant the application access to the private signing key.

DATA maintenance Phase 1F-B introduces Schema 31 coordination without adding
automatic execution. `restore_drill_runs` is mutable operational staging for
one active bounded lease. `restore_drill_run_events` is its append-only
lifecycle audit and does not replace the signed restore-evidence ledger.

PostgreSQL selects the latest eligible backup and binds the lease to its exact
backup ID and set hash. Completion requires the lease token plus a canonical
verification ID whose backup identity and report content hash match that run.
Expired leases fail explicitly; a partial unique index prevents concurrent
active runs. The DB-only coordinator cannot read signing material, backup
artifacts, reports, or active storage, while the isolated drill still cannot
access PostgreSQL.

PRODUCT-001H adds object-contextual Scientific Intelligence backed by the local
Ollama provider. Available actions depend on canonical object type; object data
is isolated from system instructions, and every response is explicitly
advisory and requires human review.

PRODUCT-001I persists AI analyses in an immutable ledger containing object,
project, actor, action, provider, model, prompt hash, output hash, and original
output. Human acceptance or rejection is a separate append-only reviewer event
with mandatory rationale. The workspace displays analysis history and exposes
review controls only to reviewers; review never mutates or promotes the source
AI output into canonical scientific knowledge.

No Neo4j, Elasticsearch, standalone vector database, or data lake is introduced
at this stage.
