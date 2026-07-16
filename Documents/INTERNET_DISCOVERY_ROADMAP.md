# Internet Discovery Roadmap

## Status

- Document status: accepted long-term implementation roadmap
- Accepted by: project owner
- Recorded: 2026-07-17
- Safety prerequisite: P0 Evidence-to-Theory Safety Gate
- Current status: P0 completed and verified
- Next deliverable: SCAN-001A Discovery Contract Foundation

This document is the canonical long-term roadmap for discovering scientific
data on the internet. Existing canonical code remains the single source of
truth for constructors, enums, lifecycle terms, service boundaries, and
dependencies. Each sprint must extend that implementation consistently rather
than rebuild it.

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
