# SGF-020 — Human Authority & Decision Matrix

## Status

- Identifier: SGF-020
- Version: 1.0
- Document status: Draft for Human Review
- Formal ratification status: pending explicit human decision under DOC-000
- Classification: scientific governance standard
- Owner: ResearchOS project
- Authority basis: DOC-000 v0.2 and canonical SGF-000 v1.0
- Recorded: 2026-07-19
- Review candidate frozen: 2026-07-19
- Historical operational source SHA-256:
  `e51beac2b7ea3d6d4e4543ec7be4e6b7e0b905614543b3cea1a566a85b47d387`
- Scope: human authority, decision admission, separation of duties, appeal,
  correction, and rollback for scientific knowledge workflows
- Depends on: SGF-000 and the permanent principles in
  `Documents/RESEARCHOS_VISION.md`
- Constrains: SGF-030, SGF-040, scientific APIs, workspace actions, automation,
  and future SGF standards

This candidate preserves operational guidance for existing and future
ResearchOS contracts. It does not claim that every control described here is
already implemented. Section 13 separates existing enforcement from required
extensions. Existing canonical code and persistence remain authoritative for
current runtime behavior until an implementation increment adopts a missing
control. Candidate status does not itself create scientific or governance
authority.

## 1. Purpose

SGF-020 answers:

- who may perform a scientific decision;
- what evidence and context must be present;
- which decisions require independent review;
- when a decision becomes stale;
- how it may be appealed, corrected, superseded, or rolled back; and
- which actions AI and infrastructure may never perform as scientific
  authority.

The standard governs authority, not expertise certification. A configured role
permits an action within ResearchOS; it does not prove that the actor has
professional, institutional, ethical, or regulatory authority outside the
system.

## 2. Permanent authority invariants

1. A machine may propose, extract, rank, summarize, translate, compare, or
   validate by an explicit method, but may not act as the human decision maker.
2. Actor identity must come from authenticated system context, never from a
   client-supplied reviewer or publisher name.
3. Every material decision requires rationale, occurrence time, object
   identity, prior state, and provenance sufficient to reproduce its context.
4. Missing authority, evidence, integrity, or freshness fails closed.
5. Read access does not imply decision authority.
6. Technical execution does not imply scientific approval.
7. A decision may not silently mutate its historical record.
8. Correction, supersession, invalidation, and rollback create new events; they
   do not erase the original decision.
9. Publication never converts an assertion into truth merely by releasing it.
10. Authorization by role is necessary but may be insufficient when this
    standard requires independence, ethics approval, or domain qualification.

## 3. Canonical actors

### 3.1 Human actor

An authenticated person accountable for an action. Every human decision record
must preserve a stable `actor_id`.

### 3.2 Service actor

A deterministic service, worker, parser, provider adapter, or scheduler.
Service actors may create observations, proposals, provisional objects, and
operational events. They may not satisfy a human-review requirement.

### 3.3 AI actor

An AI provider or model acting only as an advisory service actor. Its provider,
model, configuration, input identity, and output hash must be recorded when its
output is retained.

### 3.4 Project owner

The current project-level authority for ResearchOS governance direction. This
role does not automatically make the project owner the scientific reviewer of
every research object.

## 4. Current application roles

| Role | Existing purpose | Scientific authority boundary |
|---|---|---|
| `discoverer` | Run discovery and acquisition workflows | May enumerate and collect; cannot accept evidence or theory |
| `reviewer` | Review evidence, theory, validation inputs, lifecycle, and publication | May make implemented review decisions; independence requirements still apply |
| `indexer` | Admit eligible canonical objects to derived semantic retrieval | Cannot change scientific review state |
| `publisher` | Inspect publication readiness and release verified publication packages | Cannot accept evidence, theory, or validation inputs |
| `auditor` | Read health, audit, provenance, and verification evidence | Observation only; no decision authority |
| `admin` | Manage accounts, sessions, and operational administration | Administrative authority is not scientific authority |

An actor may hold multiple roles. Role accumulation must not be used to bypass
an explicit separation-of-duties rule. Where independent review is required,
the decision record must demonstrate distinct actor identities.

## 5. Decision classes

### 5.1 Operational determination

A deterministic result such as retrieval success, hash verification, screening
rule outcome, or validation-method result. It is reproducible output, not human
scientific approval.

### 5.2 Advisory proposal

An AI or algorithmic suggestion such as a theory proposal, alignment candidate,
translation, gap, or hypothesis. It has no canonical approval effect.

### 5.3 Human scientific decision

An authenticated judgment that changes scientific admission or review state,
such as accepting evidence or theory.

### 5.4 Release decision

A human-authorized action that releases an immutable representation after all
applicable gates pass.

### 5.5 Governance decision

A bounded decision about policies, standards, architecture, or system
evolution. Governance decisions do not substitute for scientific review.

## 6. Decision admission contract

Every material human decision must contain:

- stable decision ID;
- decision type and decision value;
- target object ID, version, and content hash where applicable;
- authenticated actor ID and role;
- prior state and requested resulting state;
- rationale;
- occurred-at timestamp;
- input evidence and provenance references;
- applicable method, policy, and version;
- conflict and uncertainty disclosure;
- independence declaration when required;
- expiry or review-due condition when applicable;
- appeal and correction linkage; and
- immutable decision-record hash.

A decision is inadmissible when its reviewed content changed after the review
context was opened, its evidence cannot be resolved, its actor is missing, or
its policy version is unknown.

## 7. Canonical decision matrix

| Decision | Required authority | Required basis | Independence | Effect |
|---|---|---|---|---|
| Define research question and discovery scope | Human researcher; currently represented through authenticated workflow input | Question, scope, inclusion/exclusion rules, stopping conditions | Recommended second review for consequential studies | Creates bounded discovery intent |
| Run discovery | `discoverer` | Valid discovery contract and search plan | Not required | Creates provider observations and snapshots |
| Acquire representation | `discoverer` or deterministic service under its request | Open access, stated license, HTTPS source, provenance | Not required | Stores verified representation or metadata-only result |
| Determine screening eligibility | Deterministic screening method | Complete rule dimensions and integrity-bound source | Human review required when method returns `human_review_required` | Permits or blocks extraction; does not accept evidence |
| Extract scientific object | Parser/service actor | Eligible screened representation and extraction manifest | Not required | Creates provisional evidence only |
| Accept or reject evidence | `reviewer` | Citation fidelity, preserved context, relevance, epistemic classification, statement and manifest hashes | Reviewer should differ from manual extractor; must differ for high-consequence profiles | Changes review admission state through append-only event |
| Admit accepted evidence to canonical graph | Deterministic admission gate; invocation currently `indexer` or workflow service | Accepted evidence and complete review provenance | No additional human judgment | Creates assertional graph; does not create fact |
| Accept or reject theory | `reviewer` | Accepted evidence, support/contradiction disclosure, rationale | Must differ from AI/service proposer; independent reviewer required for publication-grade theory | Changes theory review state |
| Align or keep theories separate | `reviewer` | Both theory identities, evidence, candidate method/score when applicable, rationale | Must not be decided by alignment algorithm | Creates explicit alignment decision |
| Assess risk of bias | `reviewer` | Theory-specific assessment basis | Independent assessment recommended; mandatory for systematic-review support | Supplies human input to validation |
| Produce validation status | Deterministic versioned method attributed to initiating `reviewer` | Fresh search boundary, evidence, replication, contradiction, bias | Method result must remain reproducible | Produces `pass`, `fail`, `incomplete`, or `stale`; not truth |
| Transition research artifact | `reviewer` in current implementation | Current state, required upstream evidence, rationale | Ratification and publication should use distinct authority in future implementation | Advances only through permitted lifecycle edge |
| Generate publication preview | `reviewer` | Theory and optional validation context | Not a release decision | Advisory preview only |
| Release publication package | `publisher` | Accepted theory, verified citations, applicable validation gate, immutable manifest | Publisher should differ from final theory reviewer for consequential outputs | Creates immutable released representation |
| Add semantic index entry | `indexer` | Accepted evidence or eligible artifact and model/version metadata | Must not alter canonical object | Creates derived, rebuildable index |
| Acknowledge monitored change | Authenticated human reviewer | Change identity and rationale | Not required | Records awareness; does not resolve scientific effect |
| Accept AI analysis | `reviewer` | Original immutable AI output, actor, rationale | Human must not be represented by AI actor | Records review of analysis; does not automatically promote source object |

## 8. Separation of duties

### 8.1 Mandatory rules

- AI proposer and human reviewer must be different actor classes.
- A service that extracts evidence may not satisfy human evidence review.
- An indexer may not manufacture an accepted state.
- An administrator may not use account authority as scientific authority.
- An auditor may not convert audit findings into scientific decisions.
- A publication release may not bypass theory acceptance, citation
  verification, or applicable validation.

### 8.2 Consequential-research profile

For medical, legal, safety-critical, human-subject, regulatory, or other
consequential research, ResearchOS must require:

- at least two distinct human reviewers for evidence or theory acceptance;
- disclosure of conflicts of interest;
- applicable ethics or institutional approval reference;
- a distinct release authority; and
- explicit review expiry.

This profile is a normative requirement but is not fully implemented in the
current role model.

## 9. Freshness, expiry, and stale decisions

A decision becomes stale when any of the following occurs:

- the reviewed object content hash or version changes;
- linked evidence is corrected, rejected, retracted, or superseded;
- a validation search exceeds its configured maximum age;
- the governing method or policy is withdrawn;
- a material contradiction is admitted;
- an ethics or access authorization expires; or
- an explicit review-due date passes.

Staleness does not erase the historical decision. It blocks downstream actions
that require a current decision and creates a review requirement.

## 10. Appeal, correction, supersession, and rollback

### 10.1 Appeal

An appeal is a request for a new independent review. It must identify the
contested decision, grounds, supporting evidence, requester, and requested
remedy. Appeal does not suspend a decision unless policy explicitly says so.

### 10.2 Factual correction

Corrects a demonstrable recording error without pretending the original record
never existed. It must point to both old and corrected values.

### 10.3 Supersession

Replaces the current normative or scientific decision after a new review. Both
records remain accessible.

### 10.4 Invalidation

Marks a decision unusable because integrity, authority, provenance, or policy
requirements were not satisfied.

### 10.5 Rollback

Restores an earlier operational state only through a new authorized transition.
Immutable evidence, publications, provenance, and decision records are never
deleted or rewritten by rollback.

Evidence and theory acceptance currently use a latest-event projection, while
artifact lifecycle is forward-only. Reverse artifact transitions require a
future explicit correction or supersession contract and must not be simulated
by direct database mutation.

## 11. UI and API requirements

The UI and API must:

- show the authenticated actor, target object, prior state, and effect before a
  material decision;
- obtain rationale and structured assessment where required;
- show conflicts, missing evidence, stale context, and policy gates;
- never render an unavailable action as implicitly approved;
- derive available actions from backend authorization;
- distinguish preview, proposal, decision, validation, and release;
- use CSRF protection for cookie-authenticated mutations; and
- display append-only decision history.

## 12. AI restrictions

AI must not:

- submit an accepted or rejected review as a human;
- choose its own reviewer identity;
- convert confidence into truth;
- hide conflicting or rejected evidence;
- silently select evidence to support a preferred theory;
- release a publication;
- grant a waiver or ethics approval; or
- change governance, ontology, lifecycle, or implementation without the
  applicable human decision.

## 13. Implementation traceability

### 13.1 Existing enforcement

- fail-closed bearer and session authentication;
- roles `admin`, `discoverer`, `auditor`, `reviewer`, `indexer`, and
  `publisher`;
- authenticated reviewer identity;
- mandatory rationale for evidence and theory decisions;
- evidence content/manifest hash binding;
- structured evidence acceptance criteria;
- append-only evidence and provenance events;
- accepted-evidence admission gate for canonical graph;
- versioned validation method and stale status;
- verified citation and validation release gates;
- immutable publication representations;
- CSRF for cookie-authenticated mutations.

### 13.2 Required extensions

- explicit researcher role;
- configurable consequential-research profile;
- multi-reviewer quorum and conflict-of-interest records;
- appeal, correction, invalidation, and supersession APIs;
- decision expiry and review-due scheduling;
- explicit ethics approval references;
- separation-of-duties enforcement across actor identities;
- distinct release approval from publication generation; and
- a canonical decision registry aligned with future SGF-060.

These extensions are requirements, not claims of current availability.

### 13.3 SGF-020A implementation record

SGF-020A separates scientific review from publication release:

- `publisher` is a first-class `KnowledgeRole`;
- publication readiness and released-package reads are available to reviewer
  or publisher, while preview generation remains reviewer-governed;
- publication creation requires `publisher`;
- the generic artifact lifecycle endpoint requires `publisher` specifically
  for transitions to `published`;
- role-aware object actions never offer a publish transition to a reviewer
  lacking publisher authority;
- local bootstrap creates and non-destructively upgrades publisher credentials;
  and
- API and lifecycle compliance tests verify reviewer denial, publisher
  attribution, and retained review authority boundaries.

This increment separates role authority. It does not yet enforce distinct human
identity when one principal is intentionally configured with both roles, nor
does it implement multi-person release quorum for consequential research.

### 13.4 SGF-020B semantic relation authority

Scientific relation admission now separates three authorities:

- a `discoverer` may propose a relation between accepted evidence objects and
  must provide its direction, canonical relation type, provenance object,
  rationale, and time;
- a distinct `reviewer` may accept or reject the proposal and must provide an
  attributable rationale and time; and
- an `indexer` may reference only currently accepted relation IDs during
  knowledge intake.

The API derives every actor from authentication. A proposer cannot review the
same relation, an indexer cannot create relation meaning, and structural or
lifecycle relations are excluded from this scientific-review path. Rejection
after acceptance remains an immutable later review and blocks subsequent
intake. Every successful relation-bearing intake now appends an immutable
admission event binding the relation, graph, intake, indexer, and time.
Rejection of an admitted relation makes dependent graphs and downstream theory
outputs non-current without deleting their historical snapshots.

## 14. Verification plan

Tests adopting SGF-020 must cover:

- missing, invalid, and insufficient roles;
- actor identity spoofing;
- stale content and version mismatch;
- evidence acceptance with each assessment criterion failing;
- AI/service attempts to satisfy human authority;
- duplicate and idempotent decisions;
- separation-of-duties violations;
- expired decisions;
- appeal and supersession history preservation;
- rejected evidence graph admission;
- release without applicable gates; and
- UI action parity with backend authorization.

## 15. Definition of Done

SGF-020 is complete as an operational standard when:

1. authority classes and current roles are explicit;
2. material decisions have a common admission contract;
3. the decision matrix covers discovery through publication;
4. separation of duties and consequential research are bounded;
5. freshness, appeal, correction, supersession, invalidation, and rollback are
   distinguished;
6. AI restrictions are explicit;
7. existing controls and extensions are not conflated; and
8. SGF-030 and SGF-040 use this authority model without contradiction.
