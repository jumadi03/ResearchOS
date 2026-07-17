# Architecture Law Governance Foundation

## Status

- Document status: governance audit draft
- Classification: architecture-governance audit and formalization roadmap
- Formal ratification status: not ratified
- Canonical law status: not an Architecture Law or active law bundle
- Authority: substantive decisions remain pending project-owner review
- Recorded: 2026-07-18
- Source revision audited: `9612ad5`
- Change boundary: documentation only; no law, validator, registry, lifecycle,
  fixture, or source-code change is authorized by this draft

This document records the repository state and the governance questions that
must be resolved before ResearchOS creates a repository-wide canonical law
registry or ratifies its first Architecture Law. The working title describes
the document's function. It does not establish a final document family,
identifier prefix, constitution, or governance authority.

## 1. Current State

### 1.1 Existing execution pipeline

The implemented Architecture Law execution path is:

```text
Law Bundle
  -> Law Registry
  -> Law Resolution
  -> Validator
  -> Architecture Violation
  -> Architecture Validation Result
  -> Compliance Report
  -> Human Review
  -> Architecture Review & Compliance (ARC)
```

The canonical implementation currently provides:

- immutable, versioned `ArchitectureLaw` records;
- immutable, content-addressed `ArchitectureLawBundle` records;
- a read-only per-execution `LawRegistry`;
- contextual law resolution by category, scope, enabled state, and effective
  dates;
- architecture facts linked to laws and violations;
- fail-safe validation and compliance statuses;
- deterministic compliance aggregation;
- append-only review decisions bound to graph identity and content hash;
- stale-review detection when the graph changes;
- time-bounded finding waivers;
- content-addressed ARC generation and integrity verification; and
- API registration of a law bundle for an individual architecture run.

The current executable validator capabilities are:

| Capability | Actual status | Boundary |
|---|---|---|
| Dependency/import prohibition | Implemented | Executes compatible `Dependency` law instances supplied in a run bundle |
| Package public namespace | Implemented | Executes the supported package `__init__` condition supplied in a run bundle |
| General namespace validation | `NOT_IMPLEMENTED` | Foundation only; cannot prove compliance |

An empty validation set, `NOT_IMPLEMENTED`, `NOT_RUN`, `ERROR`, or `FAIL`
cannot establish compliance or permit ARC publication.

### 1.2 Inventory interpretation

Concrete identifiers found only in tests, fixtures, examples, or validator
documentation are not evidence that a project-wide law has been ratified.
In particular, fixture identifiers such as `ALA-DEP-001`, `ALA-DEP-002`, and
`ALA-API-001` must not be promoted into the official inventory without a
separate governance decision and a traceable ratification artifact.

The repository therefore has an executable law framework and executable law
patterns, but the audit did not find a repository-wide, persisted, formally
ratified active law bundle. The phrase "ratified bundle" in implementation
documentation describes an expected input contract; it does not by itself
prove that the repository has defined a ratification authority or issued such
a bundle.

### 1.3 Authority and canonical-bundle gaps

The repository does not yet establish:

- who may propose, review, ratify, activate, except, supersede, or retire a
  law;
- a formal law identifier allocation authority;
- a repository-wide source of truth for active Architecture Laws;
- a complete law lifecycle and transition authority;
- a conflict-resolution authority or deterministic priority contract;
- a law-level exception contract;
- a normative mapping from every active law to its validator and coverage
  evidence; or
- the publication process that makes one immutable law bundle the official
  input to every architecture run.

These are governance gaps, not authorization to fill them through source-code
assumptions.

## 2. Normative Taxonomy

The following definitions are working boundaries for review. They prevent
different kinds of guidance from being promoted into Architecture Laws merely
because they are important.

| Class | Working definition | Expected enforcement |
|---|---|---|
| Architecture Principle | Stable design direction that explains the intended structure or decision basis | Guides laws and specifications; may require human interpretation |
| Architecture Law | Normative, scoped, authority-backed and traceable constraint with an auditable outcome and consequence | Automated, semi-automated, or controlled manual compliance evaluation |
| Derived Rule | Narrow rule logically derived from an approved principle or law for a defined context | Must trace to its parent authority and cannot contradict it |
| Engineering Standard | Repeatable implementation or delivery practice used to maintain quality and compatibility | Tooling, review, testing, or engineering governance |
| Scientific Governance Rule | Constraint protecting scientific validity, evidence authority, provenance, review, or human scientific responsibility | Scientific governance and domain safety gates, not automatically the Architecture Law Engine |
| Operational Policy | Rule governing deployment, access, backup, monitoring, runtime, or repository operations | Operational controls and attributable operational review |
| FMA Rule | Repository ownership, placement, naming, lifecycle, safety, or file-management requirement | File Management Architecture verification; cannot approve an architecture finding |
| Recommendation | Non-binding advice or improvement option | No PASS/FAIL claim and no compliance consequence |

Classification is determined by authority, scope, semantics, and consequence,
not by the file in which a statement appears.

### 2.1 Initial classification of audited candidates

| Candidate | Working classification | Current formalization position |
|---|---|---|
| Package-level public namespace | Candidate executable Architecture Law | Executable pattern exists; not ratified |
| Dependency direction | Candidate executable Architecture Law | Executable pattern exists; concrete official rules not ratified |
| Canonical authority | Foundational Architecture Principle | Domain-specific enforcement exists; no single law approved |
| Architecture before implementation | Governance and engineering workflow | Not an Architecture Law |
| Existing canonical code as Single Source of Truth | Engineering charter rule | Not an Architecture Law |
| Zero assumption | Engineering verification rule | Not an Architecture Law |
| One File, One Architectural Responsibility | Engineering rule, FMA extension, and review signal | Report-only; not a blocking Architecture Law |
| No unaccepted evidence | Scientific Safety and Governance rule | Enforced in the scientific path; not to be relabeled as a software Architecture Law |
| Definition-execution separation | Architecture Principle and pattern | Possible derived dependency rules require later review |
| AI replaceability | Architecture Principle | Enforceability and scope remain incomplete |
| Derived data is not canonical authority | Data-authority and governance principle | Requires domain-aware authority evidence |
| Human authority | Scientific Governance principle and operational control | Cannot be reduced to a static software validator |

This table is an inventory classification, not ratification.

## 3. Law Qualification Criteria

A rule may be proposed as an Architecture Law only when all of the following
can be demonstrated:

1. It is normative rather than descriptive or advisory.
2. It is sufficiently stable to justify formal change governance.
3. Its scope and exclusions are explicit.
4. Its governed target is identifiable.
5. Its evaluation can produce an attributable PASS/FAIL or an explicitly
   incomplete/not-applicable result.
6. It does not duplicate or ambiguously overlap an existing authority.
7. It is technology-agnostic as far as its architectural purpose permits.
8. It can be enforced or audited through reproducible evidence.
9. Violation has a defined consequence.
10. A recognized authority owns its approval and interpretation.
11. It is traceable to principles, decisions, specifications, validators, and
    evidence.
12. Its amendment, exception, supersession, and retirement require formal
    governance.

Failure to meet these criteria means the rule remains in another taxonomy
class or is marked not yet enforceable. Importance alone is insufficient.

## 4. Authority Model Gap

Future governance must assign, and keep distinguishable, the authority to:

- propose a law;
- review its architectural and compatibility effects;
- ratify it;
- activate it in the official bundle;
- approve or deny a law-level exception;
- resolve conflicts;
- supersede or amend it; and
- retire it.

This audit does not assign those roles. **Human authority decision required:**
the project must identify the responsible role or body, decision evidence,
quorum or approval rule where applicable, and delegation limits before any law
can claim ratified or active status.

The existing `law_admin` runtime role authorizes bundle registration through
the API. It is an operational permission and must not be interpreted as proof
of governance authority to ratify the bundle's contents.

## 5. Lifecycle Gap

The current law model supports enabled state and effective date boundaries,
but these fields do not constitute a complete governance lifecycle.

A future lifecycle must be capable of representing at least:

- proposal;
- review;
- ratification;
- activation;
- deprecation;
- supersession; and
- retirement.

This list describes required capabilities, not final state names or
transitions. **Human authority decision required:** lifecycle vocabulary,
allowed transitions, responsible authorities, evidence requirements,
compatibility rules, and treatment of existing bundles must be audited and
approved before implementation.

## 6. Canonical Law Bundle Requirement

ResearchOS needs one official repository-wide artifact that:

- is versioned and content-addressed;
- becomes immutable after publication;
- identifies every active law and its exact version;
- records effective dates;
- links laws to their authority and ratification evidence;
- binds each law to its executability class and validator contract;
- is the official input to every applicable architecture run;
- preserves bundle identity and provenance in compliance and ARC outputs;
- cannot be synthesized from test fixtures; and
- cannot be replaced merely through runtime access without an attributable
  governance decision.

The current per-run bundle mechanism is a useful execution contract, but it
does not establish which bundle is officially active across the repository.

**Human authority decision required:** choose the artifact format, ownership,
publication and activation process, storage location, update protocol, and
relationship between the official bundle and per-run registration.

## 7. Conflict and Priority

Validators and implementers must not resolve contradictory laws by personal
interpretation, source ordering, last-write behavior, or undocumented
specificity rules.

The following hierarchy is retained only as a review candidate:

```text
Scientific Constitution
  -> Scientific Governance
  -> Foundational Architecture Principles
  -> Architecture Laws
  -> Architecture Specifications
  -> Engineering Standards
  -> Implementation
```

It is not ratified by this document. The repository must first verify that
each level exists, has an authority, uses compatible terminology, and has a
defined relation to the others.

**Human authority decision required:** approve or replace the hierarchy and
define conflict detection, escalation, precedence, rationale, and audit
evidence. Until then, a detected conflict must block a definitive compliance
claim rather than be silently resolved.

## 8. Exception Governance

The following mechanisms have different meanings:

| Mechanism | Effect |
|---|---|
| Finding waiver | Time-bounded human disposition of a specific compliance finding; does not rewrite the law or validator result |
| Temporary compliance acceptance | Controlled acceptance of a known non-compliant condition for a defined release or scope |
| Law-level exception | Authority-approved, scoped and temporal departure from a law, with explicit provenance and consequence |
| Law amendment | Governed change to the normative content or scope of a law |
| Law supersession | Replacement of one law/version by another while preserving history and traceability |

The existing Review Engine implements append-only decisions and expiring
finding waivers. It does not implement law-level exceptions. FMA policy
exceptions are also separate and cannot approve Architecture Law findings.

**Human authority decision required:** define who can approve a law-level
exception, mandatory scope, rationale, evidence, expiry or review condition,
renewal constraints, conflict behavior, bundle representation, and ARC
disclosure.

## 9. Executability Classes

The following working classes may be used in documentation without adding a
source-code enum:

- **automated** — deterministic facts and validator logic can evaluate the law
  reproducibly;
- **semi-automated** — tooling produces facts or candidate findings, but a
  controlled human decision is required;
- **manual governance review** — the decision depends on authority,
  interpretation, or evidence that cannot be reduced safely to deterministic
  code; and
- **not yet enforceable** — required facts, validator, authority, or coverage
  proof is absent.

Manual does not mean informal. A manual review must record reviewer authority,
inputs, rationale, decision, time, governed scope, and provenance. AI may
summarize or recommend but cannot become the ratification or exception
authority.

## 10. Validator Mapping and Coverage Proof

Before an active law can claim enforcement, its governance record must map:

```text
Law
  -> Required Fact
  -> Fact Resolution
  -> Validator or Review Procedure
  -> Violation
  -> Validation Result
  -> Compliance Outcome
```

The mapping must state:

- fact source and freshness;
- validator identity and supported law version or condition;
- deterministic and manual boundaries;
- PASS, FAIL, ERROR, NOT_APPLICABLE, and incomplete semantics;
- evidence locations and provenance;
- tests for compliant, violating, missing, stale, and conflicting inputs;
- execution coverage across every governed target; and
- behavior when the validator is absent or `NOT_IMPLEMENTED`.

Validator existence is not coverage proof. Test-fixture execution is not proof
that an official law was evaluated. A law with incomplete target coverage
must not produce repository-wide compliance.

## 11. Decisions Reserved for Human Governance

This draft intentionally leaves the following substantive decisions open:

- final document name, family, and identifier;
- the definition and authority hierarchy of governing instruments;
- proposer, reviewer, ratifier, activation, exception, supersession, and
  retirement authorities;
- lifecycle terminology and transitions;
- law ID convention;
- official bundle format, location, activation, and publication process;
- conflict hierarchy and resolution rules;
- law-level exception contract;
- criteria for temporary compliance acceptance;
- executability-class representation in canonical contracts;
- first laws selected for formalization; and
- the threshold and evidence required for coverage certification.

None of these may be inferred from this draft or implemented before explicit
review and approval.

## 12. Formalization Roadmap

Formalization should proceed through independently reviewable deliverables:

```text
Inventory Stabilization
  -> Taxonomy Approval
  -> Authority Definition
  -> Lifecycle Definition
  -> Canonical Law Bundle Design
  -> Conflict and Exception Governance
  -> Validator Mapping
  -> Coverage Proof
  -> First Law Ratification
  -> Consolidation Review
```

### Stage gates

1. **Inventory Stabilization** — verify concrete laws, patterns, fixtures,
   documentation statements, validators, and overlaps without promotion.
2. **Taxonomy Approval** — approve boundaries between law and non-law classes.
3. **Authority Definition** — establish attributable human authorities and
   decision records.
4. **Lifecycle Definition** — approve states, transitions, evidence, and
   compatibility rules.
5. **Canonical Law Bundle Design** — design, but do not populate, the official
   repository-wide publication contract.
6. **Conflict and Exception Governance** — approve precedence, escalation, and
   law-level exception semantics.
7. **Validator Mapping** — bind proposed laws to facts, validators or manual
   procedures, and outcomes.
8. **Coverage Proof** — demonstrate target and failure-mode coverage.
9. **First Law Ratification** — ratify only reviewed, qualified laws through
   the approved authority and lifecycle.
10. **Consolidation Review** — audit duplication, usability, provenance,
    compatibility, and operational adoption.

Each stage requires its own review outcome. Completion of an earlier stage
does not imply approval of a later one.

## 13. Traceability to Existing Repository Authority

This draft was checked against:

- [`ARCHITECTURE_GOVERNANCE.md`](ARCHITECTURE_GOVERNANCE.md) for the existing
  Law Engine, compliance, review, waiver, fail-safe, and ARC contracts;
- [`LONG_TERM_ENGINEERING_CHARTER.md`](LONG_TERM_ENGINEERING_CHARTER.md) for
  engineering principles, canonical-code discipline, compatibility, and
  evidence-based status claims;
- [`SCIENTIFIC_GOVERNANCE_FRAMEWORK.md`](SCIENTIFIC_GOVERNANCE_FRAMEWORK.md)
  for scientific governance and human scientific authority boundaries;
- [`FILE_MANAGEMENT_ARCHITECTURE.md`](FILE_MANAGEMENT_ARCHITECTURE.md) for
  repository policy and exception boundaries;
- [`ONE_FILE_ONE_ARCHITECTURAL_RESPONSIBILITY.md`](ONE_FILE_ONE_ARCHITECTURAL_RESPONSIBILITY.md)
  for OFAR's report-only, non-law position; and
- the canonical models, governance services, validators, API, and tests under
  `AI-Gateway/app/architecture/`.

No dedicated documentation validator or ratification registry was identified
for this document class. Until one exists, validation consists of
reproducible link-target checks, terminology searches, traceability review,
diff validation, and confirmation that source code remains unchanged.

## 14. Draft Acceptance Boundary

Acceptance of this audit draft would establish only:

- the verified current-state inventory;
- the working taxonomy;
- the documented governance gaps;
- the separation of finding waiver from law-level exception; and
- the staged formalization roadmap.

It would not ratify a law, promote a fixture, create an active bundle, approve
the candidate hierarchy, assign an authority, or authorize implementation.

