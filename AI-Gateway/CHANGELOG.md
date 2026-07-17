# Changelog

All notable changes to ResearchOS are documented in this file. The project
follows Semantic Versioning.

## [Unreleased]

### Changed

- Added Phase 1F-E Windows host-trigger contract with read-only planning and
  status, disabled-by-default installation, limited interactive privilege,
  single-instance execution, and explicit removal that preserves canonical
  schedule and restore evidence.
- Added Phase 1F-D Schema 32 canonical restore-drill schedule governance with
  a fail-closed paused default, bounded cadence, PostgreSQL due decisions,
  duplicate-trigger suppression, and append-only policy and slot provenance.
- Added Phase 1F-C manually invoked end-to-end restore-drill control, composing
  the canonical lease, isolated drill, signed admission, and completion gates
  while failing the lease explicitly when any post-acquisition stage fails.
- Added Phase 1F-B Schema 31 exclusive restore-drill coordination with
  server-selected backup binding, bounded lease ownership, immutable lifecycle
  events, and completion tied to canonical signed verification evidence.
- Added Phase 1F-A live restore-evidence freshness enforcement, separating
  trusted cryptographic verification from bounded evidence age and requiring
  both before `recovery_ready` can become true.
- Added Phase 1E signed restore-evidence admission with Ed25519 report
  attestations, a committed public-key trust registry, schema 30 guarded and
  idempotent ledger admission, and live trust revalidation before
  `recovery_ready` can become true.
- Added the Phase 1D isolated restore-drill executor for all six manifest-bound
  backup components. The drill uses an internal-only network, executor-owned
  PostgreSQL database and MinIO bucket, tmpfs targets, read-only backup input,
  fail-closed archive extraction, full cleanup, and a hash-bound report without
  writing operational restore evidence.
- Extended portable backup sets to stable, symlink-free snapshots of
  architecture, allowlisted non-secret configuration, and versioned migration
  sources, completing six-component coverage for a future isolated restore drill.
- Added a versioned, report-only recovery coverage matrix and fail-closed
  verifier for PostgreSQL, MinIO, knowledge, architecture, configuration, and
  migration recovery paths without executing a restore or exposing secrets.
- Added schema 29 portable backup-set manifests and an immutable,
  isolated-target restore-verification contract; recovery readiness now
  requires both manifest-bound archive integrity and matching restore evidence.
- Added project-wide generation of missing Bahasa Indonesia object
  representations and switched graph node labels to available Indonesian text,
  while retaining bilingual source/translation detail views.
- Hardened GitHub container contract builds with Docker daemon diagnostics and
  three bounded, backoff retries. Deterministic failures remain blocking after
  the final attempt while transient runner/registry failures self-recover.
- Extended bilingual representations to scientific documents, evidence,
  artifacts, library cards, inspector titles, and graph focus content using
  object/source hashes, AI or manual translation, and immutable reviewer
  correction while displaying source and Indonesian text together.
- Added global bilingual UI localization with Bahasa Indonesia as the persisted
  default, source/English switching, dynamic DOM localization, translated
  placeholders and accessibility labels, and protection for scientific source
  content, identifiers, hashes, and provenance.
- Added source-bound Bahasa Indonesia theory representations with AI-assisted
  generation, manual reviewer entry, immutable source hashes, human correction
  and review, stale-translation suppression, and an Original/Indonesia toggle.
- Added a stratified blind calibration queue with balanced score bands,
  independent dual review, reviewer exclusion, agreement measurement, and
  third-reviewer adjudication before labels enter threshold calibration.
- Added a two-person calibration and promotion gate for theory alignment
  thresholds, requiring 30 labeled reviewer outcomes, observed and benchmark
  quality floors, immutable version snapshots, restart-safe activation, and
  audited rollback.
- Added versioned theory-alignment quality evaluation with immutable candidate
  score snapshots, observed reviewer outcomes, score distributions, benchmark
  precision/recall, and non-mutating threshold simulation in the workspace.
- Restricted theory review, theory validation, and knowledge publication to
  authenticated reviewer principals.
- Added explicit metadata enrichment status and counts for records,
  observations, citation edges, and conflicts to API and workspace results.
- Exposed the closed risk-of-bias vocabulary in the validation API schema and
  reject unsupported values before service execution.

### Fixed

- Compare PostgreSQL artifact metadata by canonical JSON value so nested tuple
  metadata remains idempotent after JSON storage normalization.
- Normalize structured Crossref license records before PostgreSQL persistence
  and derive open-access state only from explicit provider or license signals.
- Resolve exact DOI queries through Crossref's work endpoint instead of relying
  on ranked bibliographic search results.
- Consolidate textually equivalent conclusions across independent knowledge
  graphs while preserving every evidence edge's graph and object provenance.
- Add reviewer-governed semantic theory alignment with required prior
  acceptance, multi-graph evidence, rationale, attribution, and immutable audit events.
- Expose a reviewer-only, advisory alignment-candidate queue using transparent
  normalized-token overlap without automatically changing theory bundles.
- Add a Theory Alignment reviewer workspace for inspecting advisory candidates,
  recording scoped statements and rationales, and confirming provenance review.
- Add a reviewer-only theory bundle registry with review, alignment, candidate,
  graph, schema, integrity, and latest-validation summaries.
- Restore integrity-verified theory bundles and validation reports from their
  persistent snapshots when the API restarts.
- Add evidence-level candidate provenance and immutable reviewer decisions to
  keep semantically distinct theory pairs separate and suppress repeat prompts.
- Add a filterable theory-alignment decision ledger with reviewer attribution,
  evidence links, validation status, and permanent audit deep-links.
- Bind validation reports to exact theory-bundle content, retain inactive
  history, link revalidation to reviewer decisions, expose transparent gate
  results, and reject publication with stale validation.
- Add a fail-closed Publication Readiness workspace with policy checklists,
  non-mutating Markdown preview, evidence briefs, reviewer confirmation, and
  restart-safe immutable package history.
- Upgrade advisory theory candidates to an explainable lexical v2 method with
  stopword filtering, term and phrase components, explicit threshold, and
  opposing-polarity exclusion.

## [0.4.0] - 2026-07-16

### Added

- Deterministic architecture graph, law, compliance, review, ARC generation,
  and immutable HTML/PDF publication pipeline.
- Scientific discovery, metadata collection, document acquisition, evidence
  extraction and review, knowledge graph, theory, gap, validation, semantic
  retrieval, and publication subsystems.
- Canonical PostgreSQL/pgvector and MinIO persistence with versioned migrations
  and storage compliance checks.
- Resilient background jobs with leases, retries, dead-letter state, hard
  execution timeouts, graceful shutdown, metrics, and alerts.
- Browser workspace, role-separated accounts, administration controls,
  session security, readiness endpoints, and structured audit logging.
- Consistent PostgreSQL, MinIO, and knowledge backups with verified restore
  evidence.
- Secure idempotent local bootstrap, open-source governance files, Dependabot,
  secret scanning, push protection, and protected quality gates.
- Reproducible release bundle with wheel, source archive, CycloneDX SBOM,
  checksums, provenance metadata, and GitHub attestation.

### Changed

- Split knowledge workspace routing, repository access, ingestion, and theory
  orchestration into explicit service boundaries.
- Consolidated runtime configuration and canonical ownership contracts.

### Security

- Added fail-closed authentication and authorization, CSRF validation,
  restrictive browser headers, credential rotation, dependency auditing, and
  private vulnerability reporting.

### Fixed

- Bootstrap canonical MinIO buckets before API, worker, and backup startup.
- Stabilized test temporary directories and isolated CI deployment contracts.

## [0.3.0] - 2026-07-14

### Added

- Initial modular FastAPI baseline with settings, routers, services, models,
  and architecture test foundations.

[Unreleased]: https://github.com/jumadi03/ResearchOS/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/jumadi03/ResearchOS/releases/tag/v0.4.0
