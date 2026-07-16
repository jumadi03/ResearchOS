# ResearchOS v0.4.0

ResearchOS v0.4.0 is the first public, reproducible release of the project.

## Highlights

- Deterministic architecture governance from graph construction through
  compliance review and immutable ARC publication.
- Provenance-first scientific discovery, evidence review, knowledge graphs,
  theory synthesis, gap detection, validation, and publication workflows.
- Canonical PostgreSQL and MinIO storage with versioned migrations,
  content-addressed representations, semantic retrieval, and integrity gates.
- Resilient background workers with leases, retry/backoff, dead-letter state,
  hard timeouts, graceful shutdown, metrics, and alerts.
- Secure browser sessions, role-separated principals, administration controls,
  readiness checks, structured audit logs, and loopback-only local services.
- Verified backups, restore evidence, dependency auditing, protected quality
  gates, secret scanning, and automated dependency updates.
- Idempotent one-command local bootstrap with automatically generated secrets
  and fail-closed protection for persisted volumes.

## Reproducibility artifacts

The release contains:

- a Python wheel for the AI Gateway;
- a deterministic source archive;
- a CycloneDX 1.5 SBOM;
- build provenance metadata;
- SHA-256 checksums; and
- a GitHub build-provenance attestation.

Verify downloaded files against `SHA256SUMS` and the GitHub attestation before
use. ResearchOS remains experimental; AI-generated material is advisory and
does not replace human scientific review or professional judgment.
