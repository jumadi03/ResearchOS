# Contributing to ResearchOS

Thank you for improving ResearchOS. Contributions should preserve the
project's provenance, reproducibility, least-privilege, and fail-closed
boundaries.

## Before starting

1. Search existing issues and pull requests.
2. Open an issue for substantial behavior, schema, or architecture changes.
3. Keep credentials, research data, generated artifacts, and local environment
   files out of commits.
4. Never edit an applied database migration; add a new numbered migration.

## Development setup

Use Python 3.13 and install the development dependencies:

```powershell
Set-Location AI-Gateway
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Run the full regression suite using a writable temporary directory:

```powershell
python -m pytest -q --basetemp=..\.tmp\pytest
```

Deployment changes should also be validated from `deploy`:

```powershell
docker compose --env-file stack.env.example -f compose.yaml config --quiet
```

## Pull requests

- Create a focused branch from the latest `main`.
- Explain the problem, the chosen boundary, and verification evidence.
- Add or update tests for behavior changes.
- Update documentation when contracts or operations change.
- Keep commits free of unrelated formatting and generated output.
- Resolve review conversations and keep history linear.

All six protected quality checks must pass before merge. AI-generated code or
text remains the contributor's responsibility and must be reviewed, tested,
and attributable like any other contribution.

## Scientific integrity

Do not introduce workflows that silently:

- represent model output as accepted evidence;
- remove source provenance or integrity hashes;
- bypass human review or publication gates;
- reinterpret confidence scores as probability of truth; or
- overwrite released, immutable artifacts.

By submitting a contribution, you agree that it is licensed under Apache-2.0.
