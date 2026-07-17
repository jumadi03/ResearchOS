# Internet Discovery Roadmap

## Status

- Document status: project-owner-accepted working roadmap
- Formal ratification status: not defined by current repository governance
- Classification: implementation roadmap
- Owner: Scientific Knowledge Subsystem
- Architectural scope: Discovery Engine
- Authority: project owner
- Recorded: 2026-07-17
- Safety prerequisite: P0 Evidence-to-Theory Safety Gate
- Completed: P0 Evidence-to-Theory Safety Gate
- Completed: SCAN-001A Discovery Contract Foundation
- Completed: SCAN-001B Canonical Source Registry
- Completed: SCAN-001C Scientific Query Planner
- Completed: SCAN-001D Source Enumerator Hardening
- Completed: SCAN-001E Controlled Web Acquisition
- Completed: SCAN-001F Raw Capture and Integrity Store
- Completed: SCAN-001G Source Inspection
- Completed: SCAN-001H Identity Resolution
- Completed: SCAN-001I Screening Engine
- Completed: SCAN-001J Evidence Extraction
- Completed: SCAN-001K Human Review
- Completed: SCAN-001L Knowledge Intake
- Completed: SCAN-001M Citation Snowballing
- Completed: SCAN-001N Continuous Monitoring
- Completed: SCAN-001O Consolidation Review
- Roadmap delivery status: P0 and SCAN-001A through SCAN-001O implemented
  and consolidation-verified
- Change policy: focused, reviewable documentation commits; no implementation
  begins from a roadmap change without deliverable-specific verification
- Related documents: `README.md`,
  `Documents/SCIENTIFIC_KNOWLEDGE_ROADMAP.md`,
  `Documents/SCIENTIFIC_DATA_STORAGE.md`, and
  `Documents/ARCHITECTURE_GOVERNANCE.md`

This document is the accepted long-term working roadmap for discovering
scientific data on the internet. The repository does not currently define a
formal roadmap ID family or documentation-ratification lifecycle, so this
document does not claim a new ID, `Ratified`, `Published`, or `Canonical
Edition` status. Existing canonical code and accepted architecture documents
remain the single source of truth for constructors, enums, lifecycle terms,
service boundaries, and dependencies. Each sprint must extend that
implementation consistently rather than rebuild it.

## Scientific position

The internet is a discovery space for candidate evidence, not a source of
truth. Internet data may enter the ResearchOS knowledge layer only after
identification, normalization, integrity inspection, classification,
validation, human review, and complete provenance recording.

ResearchOS must preserve these boundaries:

```text
Internet
  -> Source Candidate
  -> Raw Representation
  -> Source Facts
  -> Canonical Document
  -> Evidence Candidate
  -> Human-Validated Evidence
  -> Scientific Knowledge
  -> Research Artifact
```

Scanning must never jump directly from a web page to canonical knowledge or
theory construction. AI is an instrument; humans remain the final scientific
authority.

## Architectural position

Internet discovery belongs in the Scientific Knowledge Subsystem under the
Discovery Engine:

```text
Scientific Knowledge Subsystem
  -> Discovery Engine
     -> Query Planning Capability
     -> Source Discovery Capability
     -> Web Acquisition Capability
     -> Metadata Inspection Capability
     -> Content Normalization Capability
     -> Screening Capability
     -> Evidence Candidate Registration
```

It is not part of the Kernel. The Discovery Engine operates above the Kernel
contracts for Project, Workspace, Workflow, Task, Context, and Artifact.

## Official implementation order

1. P0 — Evidence-to-Theory Safety Gate
2. SCAN-001A — Discovery Contract Foundation
3. SCAN-001B — Canonical Source Registry
4. SCAN-001C — Scientific Query Planner
5. SCAN-001D — Source Enumerator Hardening

P0 is complete. SCAN-001A through SCAN-001D must harden existing
implementations rather than replace them.

## Canonical pipeline

```text
Research Question
  -> Discovery Scope
  -> Source Policy
  -> Query Plan
  -> Source Enumeration
  -> Retrieval
  -> Raw Capture
  -> Metadata Inspection
  -> Normalization
  -> Deduplication
  -> Relevance Screening
  -> Evidence Eligibility
  -> Evidence Extraction
  -> Human Review
  -> Canonical Evidence
  -> Knowledge Integration
```

## Deliverable roadmap

| ID | Focus | Required output |
| --- | --- | --- |
| P0 | Evidence-to-Theory Safety Gate | Accepted-only canonical graph and theory construction with current review-state validation and complete provenance |
| SCAN-001A | Discovery Contract | Scope, inclusion and exclusion rules, evidence contract, limits, licensing, and human-review policy |
| SCAN-001B | Source Registry | Canonical source definitions, authority class, access method, rate limits, robots policy, licensing, trust profile, and status |
| SCAN-001C | Query Planner | Concept decomposition, synonym expansion, discipline mapping, query families, and source-specific queries |
| SCAN-001D | Source Enumerator | Provenance-bound candidate inventory without premature full-content retrieval |
| SCAN-001E | Controlled Acquisition | API, metadata feed, repository, HTML/XML, PDF, and general-web retrieval in that preference order |
| SCAN-001F | Raw Capture | Immutable content, headers, retrieval time, checksum, version, media type, encoding, license, and storage reference |
| SCAN-001G | Source Inspection | Factual document structure and metadata without scientific judgment |
| SCAN-001H | Identity Resolution | Identifier resolution, metadata normalization, deduplication, and canonical scientific documents |
| SCAN-001I | Screening Engine | Technical, scope, evidence, and quality screening with explicit decision reasons |
| SCAN-001J | Evidence Extraction | Claims, observations, methods, populations, variables, measurements, results, limitations, and source locations |
| SCAN-001K | Human Review | Human ratification of citation fidelity, context, relevance, confidence, and fact/interpretation separation |
| SCAN-001L | Knowledge Intake | Registration of human-accepted evidence into the Knowledge Layer |
| SCAN-001M | Citation Snowballing | Reproducible forward and backward citation traversal |
| SCAN-001N | Continuous Monitoring | Topic surveillance and source-watch workflows |
| SCAN-001O | Consolidation Review | End-to-end audit of compliance, reproducibility, provenance, and architectural boundaries |

## Discovery contract foundation

Before any internet access, the workflow must have an explicit
`DiscoveryContract` covering at least:

- discovery, project, and research-question identity;
- scope and source categories;
- inclusion and exclusion rules;
- date range, languages, and document types;
- evidence types and maximum traversal depth;
- retrieval budget and stopping conditions;
- license policy; and
- human-review policy.

The contract answers what is sought, why it is sought, which sources and data
are permitted, what qualifies as evidence, how broad the scan may become, and
when it must stop.

## Source policy

Structured scientific sources come first:

1. official API;
2. structured metadata feed;
3. open scientific repository;
4. publisher HTML or XML;
5. PDF;
6. general web page.

Initial implementation should prioritize OpenAlex, Crossref, PubMed, and other
appropriate structured scientific APIs. Publisher pages, repository PDFs, and
general-web scanning follow only after the structured pipeline is stable.

Sources require explicit authority classes:

- A1 — primary scientific source;
- A2 — curated scholarly index;
- B1 — institutional source;
- B2 — recognized professional source;
- C1 — general web source;
- C2 — unverified web source.

Authority class does not determine truth. It determines the validation burden.

## Evidence and review boundaries

ResearchOS must keep these categories separate:

- observed fact;
- source-author interpretation; and
- ResearchOS inference.

Machine-extracted evidence remains provisional until a valid human review
accepts it. P0 enforces defense in depth at intake, canonical graph
construction and persistence, and theory construction. Missing, provisional,
pending, rejected, mixed-status, stale, or incompletely provenanced evidence
must fail closed with an explicit reason.

## Capability responsibilities

- Query Planner does not retrieve documents.
- Enumerator does not judge scientific truth.
- Retriever does not perform scientific reasoning.
- Inspector does not determine theory.
- Normalizer never destroys the raw source.
- Screening Service does not write the Knowledge Graph.
- Evidence Extractor does not ratify evidence.
- AI agents do not establish scientific truth.
- Every material result is persisted as a provenance-bearing Artifact.

## Delivery discipline

For every sprint:

1. verify actual constructors, enums, lifecycle, dependencies, and service
   boundaries before editing;
2. report dependency verification and architecture position;
3. deliver one independently testable capability;
4. preserve existing terminology and contracts unless an architectural need
   requires a compatible extension;
5. run focused tests, the full regression suite, architecture compliance
   checks, and relevant PostgreSQL/MinIO verifiers;
6. report changed files, extended contracts, enforced invariants, test
   results, and remaining risks; and
7. proceed to the next deliverable only after the current one is validated.

## Governance and traceability

This document remains a roadmap. It is not an Architecture Definition
Framework, Architecture Component Specification, Architecture Law Artifact,
decision record, or scientific Artifact.

Its governance position and intended traceability are:

```text
Scientific Principles
  -> ResearchOS Project Context
  -> Internet Discovery Roadmap
  -> Sprint
  -> Architecture or Component Specification
  -> Implementation
  -> Tests and Verifiers
  -> Compliance Review
```

No standalone Project Master Context, glossary, decision repository, formal
roadmap document family, or documentation-ratification lifecycle exists in the
repository at the time of this review. Those are governance gaps, not implicit
authorization to invent identifiers or statuses.

### P0 implementation traceability

P0 is implemented and verified through the following existing paths:

- extraction lifecycle:
  `AI-Gateway/app/knowledge/extraction/models.py`;
- admission invariant and graph construction:
  `AI-Gateway/app/knowledge/modeling/admission.py`,
  `AI-Gateway/app/knowledge/modeling/models.py`, and
  `AI-Gateway/app/knowledge/modeling/graph_builder.py`;
- graph snapshot validation:
  `AI-Gateway/app/knowledge/modeling/persistence.py`;
- repository contract and PostgreSQL authority:
  `AI-Gateway/app/knowledge/repositories/contracts.py` and
  `AI-Gateway/app/knowledge/repositories/postgres_evidence.py`;
- intake and service boundaries:
  `AI-Gateway/app/knowledge/ingestion_pipeline.py` and
  `AI-Gateway/app/router/knowledge.py`;
- final theory validation:
  `AI-Gateway/app/knowledge/theory/builder.py` and
  `AI-Gateway/app/knowledge/theory_pipeline.py`;
- domain, API, and theory regression:
  `AI-Gateway/app/knowledge/tests/test_knowledge_graph.py`,
  `AI-Gateway/app/knowledge/tests/test_knowledge_api.py`, and
  `AI-Gateway/app/knowledge/tests/test_theory_builder.py`;
- canonical storage verification:
  `deploy/verify/canonical_evidence.py` and
  `deploy/verify/canonical_graph.py`; and
- integration and compliance execution:
  `.github/workflows/architecture-quality-gates.yml`.

Future SCAN deliverables must add verified traceability to their actual
component specifications, implementation paths, tests, verifiers, and
compliance closure. Paths must never be added from assumption.

### SCAN-001L implementation traceability

SCAN-001L registers only human-accepted evidence in the Knowledge Layer:

- immutable intake contract and portable snapshot:
  `AI-Gateway/app/knowledge/intake/models.py` and
  `AI-Gateway/app/knowledge/intake/persistence.py`;
- canonical extraction reconstruction and accepted-only orchestration:
  `AI-Gateway/app/knowledge/ingestion_pipeline.py`;
- admission, graph, and direct-persistence defense in depth:
  `AI-Gateway/app/knowledge/modeling/admission.py`,
  `AI-Gateway/app/knowledge/modeling/models.py`, and
  `AI-Gateway/app/knowledge/modeling/graph_builder.py`;
- repository port and PostgreSQL authority:
  `AI-Gateway/app/knowledge/repositories/contracts.py` and
  `AI-Gateway/app/knowledge/repositories/postgres_evidence.py`;
- authenticated application and API boundary:
  `AI-Gateway/app/knowledge/service.py`,
  `AI-Gateway/app/models/knowledge.py`, and
  `AI-Gateway/app/router/knowledge.py`;
- schema and immutable intake ledger:
  `deploy/postgres/init/023_knowledge_intake.sql` and
  `deploy/postgres/init/024_extraction_object_order.sql`;
- domain and API regression:
  `AI-Gateway/app/knowledge/tests/test_knowledge_intake.py`,
  `AI-Gateway/app/knowledge/tests/test_knowledge_graph.py`, and
  `AI-Gateway/app/knowledge/tests/test_knowledge_api.py`; and
- canonical reconstruction, intake, graph, and storage verification:
  `deploy/verify/canonical_evidence.py`,
  `deploy/verify/canonical_graph.py`,
  `deploy/verify/canonical_storage_healthcheck.sql`, and
  `deploy/verify/storage_compliance.py`.

Knowledge Intake reloads the immutable extraction from PostgreSQL, records
explicit admitted and excluded evidence decisions, revalidates structured
human-review provenance, persists the accepted-only graph and intake ledger in
one transaction, and writes filesystem snapshots only after canonical
persistence succeeds. Extraction object ordinal is retained so reconstruction
after restart remains byte-stable and content-hash verifiable.

### SCAN-001M implementation traceability

SCAN-001M performs reproducible, contract-bound forward and backward citation
traversal without promoting citation candidates to evidence:

- traversal contract, candidate inventory, citation edges, partial failures,
  stopping reasons, deterministic manifest identity, depth and budget
  enforcement, cycle prevention, and integrity verification:
  `AI-Gateway/app/knowledge/retrieval/snowballing.py`;
- content-addressed portable traversal snapshot:
  `AI-Gateway/app/knowledge/retrieval/snowballing_persistence.py`;
- official-provider boundaries and explicit direction capabilities for
  OpenAlex, Crossref, and Semantic Scholar:
  `AI-Gateway/app/knowledge/discovery/providers.py`;
- application orchestration and authenticated service/API boundary:
  `AI-Gateway/app/knowledge/ingestion_pipeline.py`,
  `AI-Gateway/app/knowledge/service.py`,
  `AI-Gateway/app/models/knowledge.py`, and
  `AI-Gateway/app/router/knowledge.py`;
- canonical repository port and append-only PostgreSQL persistence:
  `AI-Gateway/app/knowledge/repositories/contracts.py`,
  `AI-Gateway/app/knowledge/repositories/postgres.py`,
  `deploy/postgres/init/025_citation_snowballing.sql`, and
  `deploy/postgres/init/026_citation_candidate_inventory.sql`;
- domain and API regression:
  `AI-Gateway/app/knowledge/tests/test_citation_snowballing.py` and
  `AI-Gateway/app/knowledge/tests/test_knowledge_api.py`; and
- canonical schema, idempotency, storage contract, and integrity verification:
  `deploy/verify/canonical_repository.py`,
  `deploy/verify/canonical_storage_healthcheck.sql`, and
  `deploy/verify/storage_compliance.py`.

Every traversal remains bound to the seed's canonical identity-resolution
record and the originating `DiscoveryContract`. Candidate records preserve
provider identity, title, DOI when supplied, depth, response hash, and request
URL. Citation direction does not imply support, contradiction, relevance, or
scientific acceptance. Every candidate must return through normal discovery,
screening, extraction, and human-review boundaries before entering canonical
knowledge.

### SCAN-001N implementation traceability

SCAN-001N adds contract-bound continuous monitoring without creating a second
scheduler or promoting detected changes directly into evidence:

- immutable watch, monitoring-run, and scientific-change contracts plus
  deterministic comparison:
  `AI-Gateway/app/knowledge/monitoring/models.py`,
  `AI-Gateway/app/knowledge/monitoring/engine.py`, and
  `AI-Gateway/app/knowledge/monitoring/serialization.py`;
- canonical PostgreSQL definition ledger, mutable schedule state, immutable
  run/change/acknowledgement ledgers, and schema version 27:
  `AI-Gateway/app/knowledge/repositories/postgres_monitoring.py` and
  `deploy/postgres/init/027_continuous_scientific_monitoring.sql`;
- deduplicated scheduling and isolated execution through the existing
  resilient background worker:
  `AI-Gateway/app/workers/main.py` and
  `AI-Gateway/app/knowledge/monitoring/executor.py`;
- authenticated API creation, listing, and actor-attributed acknowledgement:
  `AI-Gateway/app/knowledge/service.py`,
  `AI-Gateway/app/models/knowledge.py`, and
  `AI-Gateway/app/router/knowledge.py`; and
- domain, regression, architecture, storage, and runtime verification:
  `AI-Gateway/app/knowledge/tests/test_continuous_monitoring.py`,
  `deploy/verify/canonical_storage_healthcheck.sql`, and
  `deploy/verify/storage_compliance.py`.

Every watch is bound to the exact canonical question, discovery contract,
planned query, and source definitions of its baseline. Paused or expired
watches are not scheduled; schedule identity is deduplicated; provider
failures remain explicit; and a missing result is never labeled unavailable
without affirmative provider evidence. Detected changes remain discovery
candidates and must pass normal screening, extraction, human review, and
knowledge-intake gates.

### SCAN-001O implementation traceability

SCAN-001O closes the roadmap with an end-to-end consolidation review and
hardens the continuous-monitoring boundary discovered during that review:

- the monitoring executor depends on injected repository and provider ports,
  while the worker remains the composition root:
  `AI-Gateway/app/knowledge/monitoring/executor.py` and
  `AI-Gateway/app/workers/main.py`;
- owner-authorized, immutable pause/resume transitions and queryable
  monitoring-run/change ledgers:
  `AI-Gateway/app/knowledge/monitoring/models.py`,
  `AI-Gateway/app/knowledge/repositories/postgres_monitoring.py`, and
  `deploy/postgres/init/028_monitoring_lifecycle_and_reads.sql`;
- authenticated lifecycle and read APIs:
  `AI-Gateway/app/models/knowledge.py`,
  `AI-Gateway/app/knowledge/service.py`, and
  `AI-Gateway/app/router/knowledge.py`;
- executable architecture and PostgreSQL integration checks:
  `AI-Gateway/app/architecture/tests/test_ci_resilience.py` and
  `deploy/verify/continuous_monitoring.py`; and
- the path-verified capability matrix, safety proof, and residual-risk record:
  `Documents/INTERNET_DISCOVERY_CONSOLIDATION_REPORT.md`.

Monitoring changes remain discovery-only candidates. Lifecycle actions are
actor-attributed, restricted to the watch owner, and stored as immutable
events. The integration verifier proves idempotent persistence, read-model
availability, acknowledgement provenance, and the absence of direct evidence
or canonical-knowledge promotion.

## Canonical documentation review protocol

Before this roadmap or a related governance document is pushed, the reviewer
must perform the following focused review. This protocol governs documentation
placement and traceability; it does not authorize implementation work.

### Dependency verification

- Inspect `README.md`, this roadmap, the applicable project context, active
  roadmaps, documentation naming and metadata patterns, relevant terminology,
  any decision repository, and the structure of `Documents/`.
- Determine which standards and canonical terms actually exist.
- Verify whether roadmap prefixes and document statuses have defined meanings.
- Make no documentation change until this verification and the governance
  position are complete and reported.

### Architecture and governance position

- Confirm ownership by the Scientific Knowledge Subsystem and architectural
  placement under the Discovery Engine.
- Preserve the relationship among scientific principles, project context,
  this roadmap, sprint, component specification, implementation, tests, and
  compliance review.
- Do not relabel the roadmap as another document or Artifact type.

### Canonical document review

- Evaluate title, version, status, classification, owner, authority, purpose,
  scope, related documents, traceability, revision history, and change policy.
- Use a document ID or lifecycle status only when repository governance
  already defines it.
- If no official family exists, report the gap and retain the existing file
  name rather than silently creating a prefix.

### Content integrity review

- Preserve the scientific principles, canonical pipeline, P0-before-SCAN
  safety correction, SCAN-001A through SCAN-001O roadmap, and capability
  boundaries in this document.
- Preserve the rule that provisional, pending, rejected, missing-review, or
  incompletely provenanced evidence cannot enter canonical knowledge or
  theory construction.
- Keep structured scientific APIs ahead of general-web crawling.

### Traceability and README review

- Verify every referenced implementation path instead of assuming it.
- Ensure the README link is relative, valid, consistently named, appropriately
  placed, and does not duplicate the roadmap.
- Ensure readers can identify the governing principle, owning subsystem,
  implementing sprint, derived specification, code, tests, verifier, and
  compliance closure.

### Required validation

- Run repository-provided documentation lint, link validation, consistency,
  and architecture/document compliance checks when they exist.
- Always run `git diff --check`.
- Reproducibly inspect local Markdown links when no dedicated validator exists.
- Confirm that only intended documentation files changed and no source code
  changed.
- Report missing validation tooling rather than building a large new system
  during a documentation-only sprint.

### Commit discipline

- Keep documentation changes in focused follow-up commits.
- Do not amend, rebase, force-push, open a pull request, or push before review,
  verification, reporting, and project-owner approval.
- Do not mix implementation changes into a documentation-review commit.

### Documentation review Definition of Done

- [ ] Dependency verification is complete and reported.
- [ ] Governance position is explicit.
- [ ] No unsupported document prefix, type, or lifecycle status was created.
- [ ] Status reflects the actual repository governance.
- [ ] Principles, pipeline, P0, SCAN-001A through SCAN-001O, and capability
  boundaries remain intact.
- [ ] Roadmap-to-implementation traceability is clear and path-verified.
- [ ] README link is valid.
- [ ] No source code changed.
- [ ] Available documentation and repository validations pass.
- [ ] Changes remain unpushed until project-owner approval.
- [ ] Working tree and commit position are reported.
- [ ] Governance gaps, tooling gaps, and recommendations are separated from
  actual changes.

## Mandatory implementation checklist

This checklist is a permanent gate for every implementation sprint. Work must
not be declared complete until every applicable item has been examined,
reported, and satisfied.

### 1. Dependency Verification

- [ ] Existing canonical code has been identified and verified.

### 2. Architecture Position

- [ ] Layer is explicit and correct.
- [ ] Subsystem is explicit and correct.
- [ ] Engine ownership is explicit and correct.
- [ ] Capability boundary is explicit and correct.

### 3. Contract Review

- [ ] Existing contract has been inspected.
- [ ] Required extension is explicit and minimal.
- [ ] Backward and architectural compatibility have been verified.

### 4. Domain Invariant

- [ ] New invariant is stated explicitly.
- [ ] Conditions that must never be violated are stated explicitly.

### 5. Safety Review

- [ ] All possible bypass paths have been examined and closed.
- [ ] Stale-state behavior has been examined and fails safely.
- [ ] Provenance remains complete and intact across every boundary.

### 6. Test Plan

- [ ] Unit tests cover domain behavior and explicit rejection reasons.
- [ ] Integration tests cover actual service and persistence boundaries.
- [ ] Architecture tests enforce ownership and dependency boundaries.
- [ ] Compliance tests verify the accepted scientific and governance rules.

### 7. Definition of Done

- [ ] A deliverable-specific Definition of Done is written before
  implementation.
- [ ] Every Definition of Done item has objective verification evidence.
- [ ] Existing tests remain successful.
- [ ] Changed files, contracts, invariants, test results, and residual risks
  are reported.
- [ ] The sprint is not advanced until the Definition of Done is satisfied.
