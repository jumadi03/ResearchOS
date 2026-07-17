# Governance Instrument Status and Decision Boundary Specification

## Status

- Document status: project-owner-accepted working specification
- Version: 0.1 working specification
- Identifier: not assigned
- Classification: project-governance working specification
- Working owner: ResearchOS project
- Decision status: accepted as bounded working direction
- Formal ratification status: not defined by current repository governance
- Enforcement status: not implemented
- Recorded: 2026-07-18
- Evidence basis: Stage 0 Dependency Verification and Phase Inventory; Stage 1
  Governance Architecture Review; Stage 2 Governance Consolidation Review

This specification does not declare itself canonical, ratified, published,
active, or approved as binding governance. The project owner reviewed exact
draft revision `a113a23b4edea2f0540d562c9d42d47c3fe30f61` and recorded a
bounded working-direction decision in pull request `#26`. This specification
does not alter the status of any existing document or governance instrument.
Its working title describes its function and does not establish a document
family or identifier convention.

## 1. Purpose

ResearchOS needs an explicit boundary between:

- statements about the maturity or effect of a governance instrument;
- evidence supporting those statements;
- operational permissions;
- governance authority; and
- the decision that permits a status claim to be used.

This specification defines the minimum information and decision boundaries
required for a governance-instrument status claim to be understandable,
attributable, reviewable, and non-self-authorizing.

It is intended to prevent a document, registry, law bundle, roadmap, audit, or
other governance instrument from becoming authoritative merely because it
labels itself `accepted`, `approved`, `ratified`, `canonical`, `published`, or
`active`.

## 2. Scope

This draft applies to status claims made by or about governance instruments,
including:

- visions;
- constitutions;
- frameworks;
- standards;
- policies;
- procedures;
- workflows;
- reviews;
- audits;
- decision records;
- registries;
- roadmaps;
- operational contracts;
- compliance instruments; and
- governance evidence records.

It covers:

- the distinction between governance and governance instruments;
- the distinction between governance authority and runtime permission;
- the minimum evidence for a status claim;
- the boundary between review and decision;
- the boundary between decision and implementation;
- the prohibition on self-authorization;
- historical traceability; and
- unresolved-authority behavior.

## 3. Out of Scope

This draft does not:

- define Project Phase Governance;
- define roadmap, sprint, task, milestone, or deliverable semantics;
- create a governance-instrument registry;
- create an identifier family;
- assign a final ratification authority;
- delegate project-owner authority;
- establish cross-governance precedence;
- change any scientific, architecture, repository, review, deployment, or
  operational lifecycle;
- ratify an Architecture Law or law bundle;
- activate a governance instrument;
- change the status of an existing document;
- migrate historical status labels;
- create a validator or enforcement mechanism; or
- authorize implementation merely because this draft is accepted for further
  work.

## 4. Evidence Basis

The repository currently contains:

- project-owner-accepted visions, working architectures, roadmaps, and
  charters whose formal ratification status is explicitly undefined;
- domain status models backed by deterministic code and canonical
  persistence;
- authenticated runtime roles for architecture and scientific operations;
- content-addressed policies, registries, reports, and review artifacts;
- protected pull-request and CI workflows;
- local decision records in architecture, scientific, repository, and
  operational bounded contexts; and
- no repository-wide governance-instrument status authority.

The following existing sources remain current repository references for their
stated subjects:

- [`RESEARCHOS_VISION.md`](RESEARCHOS_VISION.md) for project intent and
  permanent principles;
- [`SCIENTIFIC_GOVERNANCE_FRAMEWORK.md`](SCIENTIFIC_GOVERNANCE_FRAMEWORK.md)
  for the accepted scientific-governance vision and its explicitly planned
  standards;
- [`ARCHITECTURE_GOVERNANCE.md`](ARCHITECTURE_GOVERNANCE.md) for implemented
  Architecture Graph, compliance, review, and ARC behavior;
- [`LONG_TERM_ENGINEERING_CHARTER.md`](LONG_TERM_ENGINEERING_CHARTER.md) for
  accepted engineering and maintenance discipline;
- [`FILE_MANAGEMENT_ARCHITECTURE.md`](FILE_MANAGEMENT_ARCHITECTURE.md) for the
  accepted working repository-management architecture;
- [`ARCHITECTURE_LAW_GOVERNANCE_AUDIT.md`](ARCHITECTURE_LAW_GOVERNANCE_AUDIT.md)
  for the audited Architecture Law governance gap; and
- canonical source code and persistence contracts for actual constructors,
  enums, lifecycle states, service boundaries, and implementation behavior.

This draft must not reinterpret a domain lifecycle or replace canonical code
with documentation.

## 5. Definitions

### 5.1 Governance

Governance is the connected system of authority, normative constraints,
decision processes, accountability, evidence, review, consequence, and
enforcement for a defined scope.

Documentation alone is not proof that governance is operating.

### 5.2 Governance instrument

A governance instrument is an artifact used to state, execute, record, or
prove governance. Examples include a law, policy, review, audit, decision
record, registry, approval record, compliance report, or publication record.

An instrument does not become governance authority merely by existing.

### 5.3 Governance authority

Governance authority is the attributable right to make a defined governance
decision for a defined scope. Authority must have an evidence basis outside
the instrument being decided.

### 5.4 Runtime permission

Runtime permission is authorization to invoke an operation, endpoint, or
service. Examples include `law_admin`, `reviewer`, `approver`, `publisher`,
`admin`, and `indexer`.

Runtime permission does not imply authority to define, ratify, supersede, or
retire the governing instrument behind that operation.

### 5.5 Status claim

A status claim is an assertion about the maturity, review position, authority
effect, applicability, or historical position of a governance instrument.

The text of a status field is not sufficient evidence for the claim.

### 5.6 Decision boundary

A decision boundary is the point at which an attributable authority evaluates
identified evidence and records a decision with an explicit scope and effect.

A review may inform a decision but is not automatically the decision.

### 5.7 Evidence record

An evidence record is an immutable or traceable artifact supporting a status
claim or decision. Evidence may include review results, repository revision,
content hash, tests, compliance results, decision rationale, or supersession
references.

## 6. Status-Claim Principles

### 6.1 No self-authorization

A governance instrument must not:

- create the authority that gives the instrument binding effect;
- declare its own ratification sufficient;
- treat its author as its approval authority without an external authority
  basis; or
- infer authority from its filename, title, identifier, directory, or version.

### 6.2 Status text is not status proof

Words such as `accepted`, `approved`, `ratified`, `canonical`, `published`,
`active`, `completed`, `verified`, `closed`, or `archived` must not be treated
as equivalent across bounded contexts.

A status claim is usable only within its stated scope and evidence boundary.

### 6.3 Domain lifecycle isolation

Governance-instrument status claims must not replace or reinterpret:

- scientific artifact lifecycle;
- evidence or theory review states;
- Architecture Review status;
- validation or compliance status;
- public-contract lifecycle;
- repository-evolution outcomes; or
- deployment and recovery outcomes.

For example, an `APPROVED` Architecture Review does not ratify a governance
document, and a `ratified` scientific artifact does not establish
documentation authority.

### 6.4 External decision basis

Any claim with governance effect requires a decision basis that is external
to the instrument. The basis must identify the existing authority, the
authority's scope, and the evidence that the authority actually made the
decision.

### 6.5 Historical preservation

A later decision must not erase an earlier instrument, status claim, review,
or rationale. Correction and replacement must remain traceable to the prior
record.

### 6.6 Fail-closed authority

When authority, scope, evidence, or decision effect is missing or ambiguous,
the instrument must be treated as non-binding. Missing authority must not be
reconstructed from convention or intent.

## 7. Status Claim Classes

The classes below describe the effect of a claim. They are not a domain
lifecycle and do not prescribe transitions.

### 7.1 Draft claim

A draft claim means the instrument is under development or review. It carries
no authority effect beyond recording the current proposal.

### 7.2 Working-direction claim

A working-direction claim means an identified authority has accepted the
instrument for bounded planning or guidance. It does not imply formal
ratification, universal precedence, implementation completion, or activation.

Existing labels such as `project-owner-accepted working roadmap` and
`project-owner-accepted working architecture` are examples that require their
scope and evidence to remain explicit.

### 7.3 Evidence-result claim

An evidence-result claim records a reproducible result such as an audit,
review, compliance outcome, test result, or verified artifact. It proves only
what the producing method and evidence support.

An evidence-result claim must not silently become a governance decision.

### 7.4 Binding-governance claim

A binding-governance claim means an instrument has enforceable governance
effect within an explicit scope.

ResearchOS does not currently have a repository-wide authority contract that
permits this specification to classify a new document as formally ratified or
globally binding. Therefore this claim class is unavailable for new global
instruments until that dependency is separately defined and accepted.

### 7.5 Historical claim

A historical claim records that an instrument has been replaced, withdrawn,
retired, or otherwise ceased to govern a scope. It requires an attributable
decision and a reference to any replacement or reason for withdrawal.

Historical classification must preserve the instrument and prior decisions.

## 8. Minimum Status-Claim Record

A governance-instrument status claim must identify:

1. instrument title and stable content identity;
2. exact version or repository revision;
3. claim class;
4. governed scope;
5. claimant or deciding actor;
6. asserted authority basis;
7. decision or evidence timestamp;
8. rationale;
9. supporting evidence;
10. intended effect;
11. explicit non-effects and exclusions;
12. unresolved dependencies;
13. review or reconsideration condition, when applicable; and
14. prior or replacement instrument references, when applicable.

If these fields are not available, the claim remains descriptive and
non-binding.

## 9. Decision Boundary

The following activities must remain distinguishable:

```text
Authorship
  -> Evidence Review
      -> Authority Review
          -> Decision Record
              -> Implementation Decision
                  -> Verification
                      -> Separate Activation Decision, when required
```

This sequence describes different activities, not a global lifecycle.

### 9.1 Authorship boundary

An author may propose content and supply evidence. Authorship does not grant
decision authority.

### 9.2 Evidence-review boundary

Review verifies consistency, repository evidence, terminology, dependencies,
risks, and compatibility. A successful review does not automatically create
governance effect.

### 9.3 Authority-review boundary

Authority review confirms whether the deciding actor has an existing,
applicable authority basis. An operational role or repository write
permission is insufficient by itself.

### 9.4 Decision-record boundary

The decision must record actor, authority basis, scope, evidence, rationale,
effect, non-effect, time, and unresolved constraints.

### 9.5 Implementation boundary

Acceptance of an instrument does not automatically authorize source-code,
schema, lifecycle, registry, deployment, or enforcement changes. Those
changes require their own approved scope and verification.

### 9.6 Activation boundary

Implementation readiness and verification do not automatically activate a
governance instrument or operational capability. Activation requires a
separate decision when the affected boundary is irreversible, security
sensitive, scientific, deployment related, or otherwise governed.

## 10. Existing Authority Boundary

Repository evidence repeatedly identifies the project owner as the authority
for accepted visions, working architectures, roadmaps, and engineering
direction. This draft recognizes that existing evidence without extending,
delegating, or redefining it.

Project-owner acceptance currently supports a bounded working-direction
claim. It must not be silently reinterpreted as:

- formal ratification;
- global binding precedence;
- implementation authorization;
- deployment authorization;
- scientific acceptance;
- Architecture compliance approval; or
- permission to bypass domain review.

Formal ratification authority remains unresolved and outside this draft.

## 11. Runtime Role Boundary

Existing runtime roles remain bounded:

| Role family | Demonstrated operational scope | Not established by the role |
|---|---|---|
| Architecture `law_admin` | Register or replace a run law bundle | Ratify Architecture Laws |
| Architecture `reviewer` | Open review and record finding decisions | Approve governance instruments |
| Architecture `approver` | Finalize Architecture Review | Ratify documentation |
| Architecture `publisher` | Publish verified ARC artifacts | Publish global governance |
| Knowledge `reviewer` | Make defined scientific review decisions | Approve architecture or project governance |
| Knowledge `admin`/`indexer` | Perform configured administration or indexing operations | Create scientific or governance authority |

An actor may hold both operational and governance authority, but each
authority basis must be recorded separately.

## 12. Compatibility With Existing Instruments

This draft does not invalidate existing status headers. Until a separately
accepted migration or documentation-governance decision exists:

- existing status text remains historical repository evidence;
- existing formal-ratification disclaimers remain in force;
- existing domain state machines remain authoritative;
- existing project-owner-accepted documents remain bounded working
  directions;
- implementation truth remains in canonical code and persistence contracts;
  and
- conflicts remain explicit rather than being normalized automatically.

## 13. Circular-Authority Guards

Review of this specification must reject any revision that:

- assigns an identifier family to itself;
- declares itself canonical, ratified, active, or globally binding;
- creates a ratification authority and immediately uses that authority on
  itself;
- treats merge access, repository ownership, or runtime permission as
  sufficient governance authority;
- reclassifies existing documents without separate evidence and decision;
- converts an evidence result directly into governance authority;
- unifies domain lifecycle terms; or
- authorizes implementation or activation implicitly.

## 14. Required Review

Review supporting a working-direction decision must verify:

- consistency with Stage 0, Stage 1, and Stage 2 evidence;
- compatibility with existing document status statements;
- separation between governance and governance instruments;
- separation between authority and runtime permission;
- absence of self-ratification;
- absence of domain-lifecycle changes;
- preservation of historical evidence;
- explicit unresolved authority gaps;
- cross-reference validity; and
- repository diff limited to documentation.

Substantive authority decisions remain reserved for external project-owner
review.

## 15. Acceptance Boundary

Acceptance of this draft would establish only a bounded working specification
for:

- evaluating governance-instrument status claims;
- recording the evidence behind those claims;
- separating review from decision;
- separating authority from runtime permission; and
- preventing self-authorization.

Acceptance would not:

- formally ratify this or another instrument;
- establish global precedence;
- create Project Phase Governance;
- approve a registry, validator, or implementation;
- activate a policy or operational capability; or
- change an existing instrument's status.

## 16. Dependencies for Later Work

Later governance work remains dependent on separate review of:

- formal authority and ratification boundaries;
- cross-governance precedence and conflict resolution;
- general decision-memory requirements;
- documentation classification and change governance;
- cross-domain terminology coordination;
- roadmap governance;
- Project Phase Governance; and
- governance coverage and traceability.

This list records dependencies only. It does not authorize or specify those
deliverables.

## 17. Governance Baseline Interface

### 17.1 Observational responsibility

A Governance Baseline is an immutable observational artifact that records a
repository-evidenced governance state within an explicit observation
boundary.

It is not:

- governance authority;
- a governance decision;
- a normative specification;
- a policy;
- a lifecycle;
- a compliance approval; or
- a replacement for canonical code or persistence authority.

The phrase `repository-evidenced state` means a state supported by verified
repository evidence. Repository presence alone is insufficient because the
repository can contain historical documents, drafts, fixtures, derived
artifacts, examples, and unverified status claims.

### 17.2 Analytical content

A Governance Baseline may contain reproducible analytical interpretation, but
must not contain normative interpretation. Its observations must distinguish:

- observed facts;
- derived relationships;
- analytical classifications;
- conflict findings;
- governance gaps;
- uncertainty;
- evidence limitations; and
- excluded or unverified claims.

Each derived relationship or analytical classification must identify the
evidence and method supporting it.

### 17.3 Observation boundary

A Governance Baseline must make its evidence boundary reproducible. The
boundary must identify at least:

- repository revision;
- observation timestamp;
- included evidence scope;
- excluded scope;
- verification method;
- known limitations;
- unresolved conflicts;
- confidence basis;
- predecessor reference, when one exists;
- correction reference, when one exists; and
- stable content identity.

This draft does not define the format, identifier, storage location, or
registry for those fields.

### 17.4 Factual correction boundary

A historical Governance Baseline must not be overwritten when a factual error
is discovered. Correction requires:

- preservation of the original baseline;
- evidence identifying the factual error;
- a traceable correction record; and
- a corrected baseline that references the original and the correction.

Factual correction is distinct from governance amendment or supersession. A
correction repairs the representation of observed evidence; it does not change
governance authority or normative effect.

### 17.5 Material-change boundary

Not every repository change requires a new Governance Baseline. A later
Architecture Review may identify a material change to:

- governance evidence;
- authority evidence;
- dependency relationships;
- lifecycle contracts;
- bounded-context positioning;
- canonical ownership;
- conflict resolution; or
- evidence that invalidates a prior analytical conclusion.

The final trigger and authority for issuing a new baseline remain unresolved
dependencies. This draft does not establish them.

### 17.6 Separation of responsibilities

The following responsibilities must remain distinguishable:

```text
Audit Evidence
  -> supports observation

Governance Baseline
  -> consolidates repository-evidenced state

Governance Specification
  -> defines normative interpretation and constraints

Authority Decision Record
  -> records an authority decision using an applicable specification

Implementation
  -> realizes an authorized decision

Verification Evidence
  -> records the observed implementation result
```

A Governance Baseline must not approve a specification. A specification must
not rewrite a historical baseline. An authority decision must not be inferred
from a baseline alone. Implementation must not begin merely because a
specification exists.

### 17.7 Bootstrap dependency

Before the first Governance Baseline exists, governance work may depend
directly on verified audit evidence. The working bootstrap dependency is:

```text
Stage 0-2 Audit Evidence
  -> Status and Decision Boundary Specification Draft
      -> review of an exact repository revision
          -> bounded project-owner working-direction decision
              -> Governance Baseline Specification Draft
                  -> Architecture Review
                      -> separate bounded working-direction decision
                          -> First Governance Baseline Snapshot
```

This sequence describes dependency and review activities. It is not a global
lifecycle, does not create a document identifier, and does not authorize the
later artifacts.

After bootstrap, the expected dependency direction is:

```text
Governance Baseline
  -> Governance Specification
      -> Authority Decision Record
          -> Implementation Authorization
              -> Implementation
                  -> Verification Evidence
                      -> Architecture Review
                          -> later Governance Baseline when material
```

The availability of an earlier artifact does not automatically authorize the
next activity.

## 18. Durable Working-Direction Decision Record

Discussion-stage agreement remains design input until an exact repository
revision and a durable external decision record exist. Those requirements were
met for the working-direction decision recorded below.

The decision was accepted only after:

1. the exact content received a stable repository revision;
2. the revision was reviewed against the requirements in Section 14;
3. the project owner made an explicit bounded decision about that exact
   revision;
4. the decision was recorded durably on the introducing pull request; and
5. its effect and non-effect were recorded without implying formal
   ratification.

### Decision

- Instrument: `Governance Instrument Status and Decision Boundary
  Specification`
- Version: `0.1 draft` at the reviewed revision
- Instrument location:
  `Documents/GOVERNANCE_INSTRUMENT_STATUS_AND_DECISION_BOUNDARY.md`
- Claim class: working-direction claim
- Deciding actor: ResearchOS project owner
- Authority basis: existing project-owner authority consistently recorded by
  ResearchOS vision, governance, roadmap, architecture, and engineering
  documents
- Reviewed revision: `a113a23b4edea2f0540d562c9d42d47c3fe30f61`
- Decision date: 2026-07-18
- Decision evidence:
  `https://github.com/jumadi03/ResearchOS/pull/26#issuecomment-5006887614`
- Scope: evaluation and recording of governance-instrument status claims and
  decision boundaries
- Rationale: ResearchOS needs an upstream, non-self-authorizing boundary before
  formal authority, documentation, roadmap, or Project Phase governance can be
  specified safely

### Bounded effect

The specification is accepted as bounded working direction for subsequent
governance analysis and specification work.

### Non-effect

This decision does not:

- formally ratify the specification;
- give it global binding precedence;
- assign an identifier;
- create or delegate ratification authority;
- activate enforcement;
- change an existing document's status;
- authorize source-code, lifecycle, registry, validator, or deployment
  changes; or
- approve any later governance deliverable.

### Supporting evidence

- Stage 0 terminology, phase, lifecycle, naming, authority, and governance
  inventory;
- Stage 1 governance landscape, dependency graph, layering, and missing
  governance analysis;
- Stage 2 artifact classification, root analysis, conflict and circular
  dependency review, construction readiness, and first-deliverable
  recommendation;
- repository documents listed in Section 4; and
- the exact repository revision reviewed by the project owner; and
- the durable pull-request decision reference recorded above.

### Unresolved dependencies

- formal ratification authority;
- cross-governance precedence;
- general decision-memory governance;
- documentation governance;
- roadmap governance;
- Project Phase Governance; and
- governance coverage mapping.

### Reconsideration condition

This working-direction decision must be reviewed if an external authority
model, documentation-governance specification, or conflicting higher-scope
governance instrument is later accepted.
