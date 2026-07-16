# Changelog

All notable changes to ResearchOS are documented in this file. The project
follows Semantic Versioning.

## [Unreleased]

### Changed

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
