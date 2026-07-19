# ResearchOS in 5 Minutes

This guide starts the public `v0.4.0` release as a private local deployment.
ResearchOS binds its user-facing services to `127.0.0.1`, generates unique
credentials, and keeps those credentials outside version control.

## 1. Check the requirements

Install and start:

- Docker Desktop with Docker Compose;
- Git; and
- Python 3.13.

In PowerShell, confirm that the tools are available:

```powershell
docker version
docker compose version
git --version
py -3.13 --version
```

Docker Desktop must be running before continuing.

## 2. Download the public release

Clone the immutable `v0.4.0` release tag and enter its directory:

```powershell
git clone --branch v0.4.0 --depth 1 https://github.com/jumadi03/ResearchOS.git
Set-Location ResearchOS
```

Using a tagged release makes the installation reproducible. The latest release
and its checksums are available on the
[ResearchOS releases page](https://github.com/jumadi03/ResearchOS/releases/tag/v0.4.0).

## 3. Start ResearchOS

Run the secure bootstrap from the repository root:

```powershell
py -3.13 Scripts\bootstrap_local.py
```

The first run builds the containers and may take longer than five minutes on a
slow network. The command:

- creates unique local credentials;
- starts PostgreSQL, MinIO, the API, workers, and monitoring;
- creates six role-separated browser accounts; and
- verifies account login, API health, and both required object-storage buckets.

The installation is ready when the command ends with:

```text
runtime-bootstrap=passed accounts=6 buckets=2
researchos-bootstrap=passed credentials=deploy/local-access.env
```

Running the command again is safe. Complete existing credentials are reused
instead of being silently replaced.

## 4. Open and verify the services

Open these local addresses:

- API health: <http://127.0.0.1:8080/health>
- Interactive API documentation: <http://127.0.0.1:8080/docs>
- MinIO console: <http://127.0.0.1:9101>
- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000>

Human workspace usernames and passwords are stored in
`deploy/local-access.env`. Infrastructure credentials are stored in
`deploy/stack.env`. View them only on your own computer and never paste them
into an issue, chat, screenshot, commit, or pull request.

To see container health without exposing credentials:

```powershell
Set-Location deploy
docker compose --env-file stack.env -f compose.yaml ps
Set-Location ..
```

## 5. Stop safely

Stop the services while preserving databases, objects, and credentials:

```powershell
Set-Location deploy
docker compose --env-file stack.env -f compose.yaml down
Set-Location ..
```

Start them again by rerunning the bootstrap command. Do not add `--volumes` to
the stop command: that option permanently deletes local databases, objects,
monitoring history, and backups.

## Troubleshooting

### Python 3.13 is not found

Install Python 3.13, reopen PowerShell, and confirm `py -3.13 --version` works.
ResearchOS `v0.4.0` requires Python 3.13.

### Docker cannot be reached

Start Docker Desktop and wait until its engine reports that it is running,
then rerun the bootstrap command.

### Local credentials are missing but volumes exist

The bootstrap deliberately stops to protect existing data. Restore the three
ignored files from the same installation:

- `deploy/stack.env`;
- `deploy/local-access.env`; and
- `deploy/monitoring/prometheus.token`.

Do not generate replacement database or object-storage passwords for existing
volumes. For more recovery and operational details, read
[ResearchOS Local Stack](LOCAL_STACK.md).

### A local port is already in use

Stop the program already using ports `8080`, `5432`, `9000`, `9101`, `9090`, or
`3000`, then rerun the bootstrap. The default Compose file intentionally binds
these services to the local computer only.

## Next steps

- Complete [your first ResearchOS workflow](FIRST_RESEARCH_WORKFLOW.md) to turn
  a research question into a provenance-bearing literature snapshot.
- Explore the interactive API at <http://127.0.0.1:8080/docs>.
- Read the [scientific knowledge roadmap](SCIENTIFIC_KNOWLEDGE_ROADMAP.md).
- Review [local deployment and operations](LOCAL_STACK.md) before changing the
  stack or restoring backups.
- Read the [security policy](../SECURITY.md) before reporting a vulnerability.
