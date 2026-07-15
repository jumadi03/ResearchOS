# ResearchOS Architecture Governance

## Purpose

ResearchOS architecture governance is a deterministic pipeline that inspects a
project, applies versioned architecture rules, records review decisions, and
produces a reproducible Architecture Review & Compliance (ARC) package.

## Canonical terminology

- **Architecture Graph** is the versioned representation of source artifacts
  and their relationships.
- **Architecture Law Engine** resolves internal software-architecture rules.
  It does not interpret legislation, regulation, privacy law, or legal advice.
- **Compliance Engine** executes deterministic validators against an
  Architecture Graph and a resolved architecture-law bundle.
- **Review Engine** records human decisions, waivers, and their rationale. It
  must not silently change validator results.
- **ARC** means **Architecture Review & Compliance**. An ARC package contains
  the graph, resolved laws, validation results, review decisions, provenance,
  and rendered reports.

If ResearchOS later supports legislation or regulatory research, that domain
must use separate names and contracts such as `LegalRule` and
`RegulatoryComplianceEngine`. It must not reuse `ArchitectureLaw`.

## Trust boundary

Deterministic code is the source of truth for scanning, graph construction,
law resolution, validation status, hashes, and release gates. AI may explain a
finding or propose remediation, but AI output is advisory and cannot directly
mark a validation as passed, approve a waiver, or issue an ARC package.

## Fail-safe compliance semantics

A report is compliant only when it contains at least one validation and every
result is either `PASS` or `NOT_APPLICABLE`.

The following statuses block compliance and ARC publication:

- `FAIL`
- `ERROR`
- `NOT_RUN`
- `NOT_IMPLEMENTED`

An empty violation list is not evidence of compliance. Foundation validators
must return `NOT_IMPLEMENTED` until they perform their documented inspection.

## Reproducibility gate

Before an ARC package can be issued, ResearchOS must persist:

- project and source revision identifiers;
- Architecture Graph identifier and content hash;
- law bundle version and content hash;
- engine and schema versions;
- complete validation results and evidence locations;
- review decisions, reviewer identity, and timestamps;
- hashes of generated Markdown, HTML, and PDF artifacts.

Persistence will be introduced after the Architecture Graph contract exists.
Until that contract is implemented, the governance pipeline must identify its
output as incomplete and must not claim ARC readiness.

## Publication model

Markdown is the canonical human-readable report. HTML and PDF are sibling
renders derived from the same Markdown report and ARC manifest:

```text
ARC data -> Markdown -> HTML
                    -> PDF
```

PDF is not used as an intermediate representation.

## Architecture Graph MVP

The current graph schema is version `1.0` and represents `Project`, `Module`,
and `Class` nodes with `CONTAINS`, `DEFINES`, and `IMPORTS` relationships.
Source paths are relative to the scan root. Nodes and edges are sorted before
serialization, and snapshot identity is derived from a SHA-256 content hash.

The graph is built with `ArchitectureGraphBuilder`. Its `source_revision`
should be populated with a commit identifier or another immutable source
revision before a snapshot is persisted or used by compliance validation.

## Architecture Law Engine MVP

Architecture laws are immutable, versioned declarations. A law can define a
category, severity, node-type and source-path scope, a declarative condition,
remediation guidance, effective dates, and an enabled flag. Dates use ISO
`YYYY-MM-DD` format.

Ratified laws are distributed as an `ArchitectureLawBundle`. Bundle laws are
canonically ordered and the JSON representation is protected by a SHA-256
content hash. Loading modified JSON fails integrity validation.

`LawResolution.resolve_context()` evaluates applicability for a category,
node type, source path, and date. Its `ResolvedLawSet` records both applicable
and excluded laws plus one trace reason for every decision. Resolution decides
which laws apply; evaluation of each law's `condition` belongs to the
Compliance Engine.

## Compliance Engine MVP

The Compliance Engine executes validators against one immutable Architecture
Graph snapshot. It currently supports these deterministic law conditions:

- Dependency: `{"relation": "IMPORTS", "forbidden_target": "pattern"}`
- Public API: `{"type": "REQUIRE_PACKAGE_INIT"}`

Dependency target patterns use shell-style matching. Validator scope is still
defined by the law's node types and source-path patterns. Findings contain a
stable fingerprint, source and target node identifiers, source path, import
line numbers where available, remediation guidance, and the graph content
hash.

A validator without a graph returns `NOT_RUN`. A supported rule with no
violation returns `PASS`; a rule outside the current target returns
`NOT_APPLICABLE`; malformed or unsupported conditions return `ERROR`. This
prevents unknown conditions from being interpreted as successful compliance.

## Review Engine MVP

A `ReviewSession` is bound to the graph identifier and content hash recorded
by one compliance report. Opening a review without this provenance is rejected.
The review identifier is deterministically derived from the graph hash,
compliance status, and finding identifiers.

Decisions are append-only. A later decision supersedes an earlier decision for
the same finding without deleting history:

- `ACCEPT` confirms the finding and remains blocking.
- `REQUEST_CHANGE` keeps the finding blocking.
- `REJECT` rejects the review.
- `FALSE_POSITIVE` resolves the finding for the current graph snapshot.
- `WAIVE` resolves the finding only through its mandatory expiry date.

A passing report with no findings can be approved directly. A failing report
is approved only when every current finding is covered by a non-expired waiver
or marked false positive. Missing decisions, accepted findings, requested
changes, and expired waivers produce `CHANGES_REQUESTED`. Incomplete compliance
can never be approved.

Every open, decision, stale transition, and finalization creates an immutable
audit event. A graph-hash change marks the session `STALE`. Review JSON and its
SHA-256 content hash are available for the future ARC manifest.

## ARC Generator MVP

ARC generation is a release operation and requires an `APPROVED` review. The
generator verifies the Architecture Graph and law-bundle content hashes,
compliance graph provenance, review graph provenance, equality of compliance
violations and review findings, and that every referenced law belongs to the
ratified bundle.

One ARC package contains:

- `architecture-graph.json`
- `laws.json`
- `compliance-report.json`
- `review.json`
- `report.md`
- `manifest.json`
- `checksums.json`

The five payload artifacts are protected by SHA-256 checksums in the manifest.
The manifest itself has a content hash and provides the content-addressed ARC
identifier. `ARCPackage.verify()` checks both levels before persistence.

Released ARC directories are immutable and cannot be overwritten. Markdown is
the canonical human-readable report;
future HTML and PDF files must be rendered from this report and added to a new
finalized manifest rather than inserted into an already-issued package.

## ARC Publisher MVP

`ARCPublisher` accepts only a verified ARC package containing canonical
`report.md`. It renders `report.html` and binary `report.pdf` as sibling output
artifacts, recalculates every payload checksum, and issues a new manifest and
ARC identifier. The original package remains unchanged.

The HTML renderer escapes untrusted content, provides responsive tables, and
includes print styling. The PDF renderer uses landscape A4 pages, consistent
typography and spacing, repeating table headers, page numbers, and a ResearchOS
footer. Both renderers support the constrained Markdown dialect generated by
`ARCGenerator`; arbitrary Markdown extensions or embedded HTML are not
executed.

ARC persistence is binary-safe. HTML and Markdown are written as UTF-8 text,
while PDF bytes are written without text conversion. Checksums are calculated
over the exact persisted bytes.

## API and orchestration MVP

`ArchitecturePipelineService` enforces the workflow order and persists a JSON
snapshot after each successful stage. The FastAPI surface is:

- `POST /architecture/runs`
- `GET /architecture/runs/{run_id}`
- `PUT /architecture/runs/{run_id}/laws`
- `POST /architecture/runs/{run_id}/compliance`
- `POST /architecture/runs/{run_id}/review`
- `POST /architecture/runs/{run_id}/review/decisions`
- `POST /architecture/runs/{run_id}/review/finalize`
- `POST /architecture/runs/{run_id}/arc`

The project scan root and output root are server configuration values. Request
contracts reject unknown fields, so a client cannot submit a filesystem root.
Re-registering a law bundle invalidates downstream compliance, review, and ARC
state. Re-running compliance invalidates review and ARC state.

Stage snapshots and final ARC packages survive process termination on disk.
At service startup, the active run index is rebuilt from content-verified graph,
law, compliance, review, and ARC snapshots. Rehydration is fail-safe and
progressive: a corrupt graph excludes the run; a corrupt downstream snapshot
is discarded together with later stages while earlier verified stages remain
available. Errors are retained in `rehydration_errors` for operational review.

Every architecture endpoint requires an opaque Bearer token. Tokens and actor
identities are mapped only in server configuration through the JSON object
`ARCHITECTURE_API_PRINCIPALS`, for example:

```json
{
  "replace-with-a-long-random-token": {
    "actor_id": "architect@example.org",
    "roles": ["reviewer", "approver", "auditor"]
  }
}
```

An empty mapping denies every request. Missing or invalid credentials return
HTTP 401 with `WWW-Authenticate: Bearer`. Reviewer and actor fields are not
accepted in request bodies; review audit identity always comes from the
authenticated principal. Production deployments must inject and rotate these
tokens through a secret manager rather than committing them to source control.

Authorization uses these least-privilege roles:

| Role | Authorized operations |
|---|---|
| `scanner` | Create a scan run and execute compliance |
| `law_admin` | Register or replace a ratified law bundle |
| `reviewer` | Open a review and record finding decisions |
| `approver` | Finalize a review |
| `publisher` | Generate and publish an ARC package |
| `auditor` | Read run status |

A valid principal without the required role receives HTTP 403. Authentication
is declared as an HTTP Bearer security scheme in OpenAPI. ARC schema `1.1`
records the authenticated publisher in `generated_by` and includes that
identity in the manifest content hash.

## Transactional persistence

Every mutable stage snapshot is committed with a same-directory temporary
file, file flush, `fsync`, and atomic replace. Readers therefore observe either
the previous complete snapshot or the next complete snapshot, never a partial
write.

Filesystem commits are serialized across service processes through the
server-controlled `.pipeline.lock`. Lock acquisition has a bounded timeout so
contention cannot block a request indefinitely.

ARC publication uses a directory transaction:

1. write the complete package into an internal `.tmp-arc-*` directory;
2. reload and verify the staged manifest, file set, and checksums;
3. atomically rename the staging directory to its content-addressed ARC name.

An existing released ARC directory is never replaced, including when the same
request is repeated. A repeated release returns HTTP 409. PDF rendering uses
ReportLab invariant mode, making PDF bytes and ARC identifiers deterministic
for identical inputs.

On startup, recovery removes only internal `.tmp-*` files and directories.
Committed ARC directories are never deleted. If a crash occurs after the ARC
directory commit but before the location pointer update, rehydration discovers
and verifies released ARC directories directly and selects the latest valid
package by generation timestamp and ARC identifier.

## Schema compatibility and migration

Schema versions use strict `major.minor` syntax and are governed by the central
registry in `app.architecture.schema`. Invalid, unknown, and future versions are
rejected before their content is used.

| Artifact | Current | Readable legacy |
|---|---:|---:|
| Architecture Graph | `1.0` | none |
| Architecture Law Bundle | `1.0` | none |
| Compliance Report | `1.0` | `0.9` |
| Review Session | `1.0` | `0.9` |
| ARC Manifest | `1.1` | `1.0` |

Compatibility reads do not silently migrate content-addressed artifacts. A
legacy compliance report or review retains its historical serialization and
hash until `upgraded()` is called. ARC manifest `1.0` remains verifiable and
`upgraded(generated_by=...)` issues a new `1.1` manifest hash and ARC identity.

Migration functions operate on copies and require a complete registered path
from source to current version. Released packages are never rewritten in
place; an upgraded package is a new release. Rehydration treats unsupported
schema errors like other integrity failures and preserves the last valid prior
stage.

## Operational observability

Every HTTP request carries an `X-Correlation-ID`. A caller-supplied identifier
is accepted only when it contains 1-128 letters, digits, dots, underscores, or
hyphens; otherwise the service generates a new identifier. The same value is
returned in the response and propagated into structured JSON logs and durable
audit events.

The operational endpoints are:

- `GET /health`: process liveness, with no authentication requirement;
- `GET /ready`: readiness of project root, output root, persistence lock, and
  authentication configuration;
- `GET /metrics`: Prometheus-compatible request and governance counters,
  restricted to the `auditor` role.

Readiness returns HTTP 503 when any required check fails. HTTP metrics use the
route template rather than concrete run identifiers to keep label cardinality
bounded. Governance metrics cover compliance executions and findings, review
finalization, and ARC publication outcomes.

Authentication failures, authorization denials, and ARC publication attempts,
successes, and failures are appended as fsynced JSON Lines records under
`<ARCHITECTURE_OUTPUT_ROOT>/audit/security-publication.jsonl`. Audit records
include the event type, actor when known, outcome, UTC timestamp, correlation
identifier, and event-specific details. They are operational evidence and do
not replace the content-addressed review audit trail embedded in an ARC.

## Continuous quality gates

The `Architecture Quality Gates` GitHub Actions workflow runs for relevant pull
requests, pushes to `main`, and manual dispatches. It grants only read access to
repository contents, disables persisted checkout credentials, cancels obsolete
runs on the same ref, and bounds each job with a timeout.

The required checks are:

- `Regression and coverage`: all tests, dependency consistency, and at least
  90% coverage over architecture, observability, and architecture API code;
- `Schema, ARC, and persistence gates`: focused compatibility, migration,
  package integrity, PDF publication, and transactional persistence tests;
- `Dependency security`: source compilation and a known-vulnerability audit of
  the installed Python environment.

Repository branch protection should require all three checks before merge.
Dependency vulnerabilities are blocking findings; they must be remediated by a
verified upgrade or addressed through a separately reviewed, time-bounded risk
acceptance process rather than silently ignored in the workflow.
