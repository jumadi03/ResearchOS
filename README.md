# ResearchOS

[![Architecture Quality Gates](https://github.com/jumadi03/ResearchOS/actions/workflows/architecture-quality-gates.yml/badge.svg)](https://github.com/jumadi03/ResearchOS/actions/workflows/architecture-quality-gates.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](AI-Gateway/pyproject.toml)

ResearchOS is an experimental, provenance-first platform for scientific
knowledge workflows and deterministic software architecture governance. It
combines a FastAPI application, PostgreSQL with pgvector, MinIO object storage,
resilient background workers, and an observable local deployment.

ResearchOS preserves a strict boundary between machine assistance and human
decisions. AI-generated material is advisory: it cannot silently promote
evidence, approve theories, or declare architecture compliance.

## Current capabilities

- Literature discovery with versioned provider snapshots and provenance.
- Content-addressed scientific document and representation storage.
- Evidence extraction, human review, knowledge graphs, and theory synthesis.
- Research-gap detection, validation reports, and reproducible publications.
- Deterministic architecture graphs, compliance review, and ARC packages.
- PostgreSQL migrations, MinIO bootstrap, background-job recovery, monitoring,
  and verified backups.
- Role-separated bearer tokens and browser sessions with auditable lifecycle.

## Project status

The project is under active development and its public interfaces may change.
It is not a substitute for scientific peer review, professional judgment, or
regulatory validation. Review the trust boundaries in the project documents
before using outputs in consequential workflows.

## Quick start

For the complete first-run walkthrough, including verification, credentials,
safe shutdown, and troubleshooting, read
[ResearchOS in 5 Minutes](Documents/GETTING_STARTED.md).

Requirements:

- Docker Desktop with Docker Compose
- Git
- Python 3.13 for local development

Clone and bootstrap the local deployment:

```powershell
git clone https://github.com/jumadi03/ResearchOS.git
Set-Location ResearchOS
py -3.13 Scripts\bootstrap_local.py
```

The bootstrap command generates unique credentials, starts the canonical stack,
creates five role-separated accounts, verifies login and MinIO access, and
stores the credentials only in ignored local files. It can be run again safely:
existing complete credentials are reused rather than silently rotated.

Never commit `deploy/stack.env`, `deploy/local-access.env`, `.env`, or
monitoring tokens. To create configuration without starting Docker, add
`--configuration-only`.

Local endpoints:

- API: `http://127.0.0.1:8080`
- API documentation: `http://127.0.0.1:8080/docs`
- MinIO console: `http://127.0.0.1:9101`
- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`

Do not run `docker compose down --volumes` unless permanent deletion of local
databases, objects, monitoring history, and backups is intended.

## Development

```powershell
Set-Location AI-Gateway
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q --basetemp=..\.tmp\pytest
```

Pull requests must pass regression, knowledge-product, deployment, storage,
schema and persistence, and dependency-security gates.

## Documentation

- [ResearchOS in 5 Minutes](Documents/GETTING_STARTED.md)
- [Your first ResearchOS workflow](Documents/FIRST_RESEARCH_WORKFLOW.md)
- [Local deployment and operations](Documents/LOCAL_STACK.md)
- [Scientific data storage architecture](Documents/SCIENTIFIC_DATA_STORAGE.md)
- [Scientific knowledge roadmap](Documents/SCIENTIFIC_KNOWLEDGE_ROADMAP.md)
- [Architecture governance](Documents/ARCHITECTURE_GOVERNANCE.md)
- [Storage compliance report](Documents/STORAGE_COMPLIANCE_REPORT.md)
- [AI Gateway details](AI-Gateway/README.md)

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report
security vulnerabilities privately according to [SECURITY.md](SECURITY.md);
do not disclose credentials or vulnerabilities in a public issue.

## Citation

Academic users can cite the project using [CITATION.cff](CITATION.cff).

## License

Copyright 2026 Jumadi. Licensed under the
[Apache License 2.0](LICENSE).
