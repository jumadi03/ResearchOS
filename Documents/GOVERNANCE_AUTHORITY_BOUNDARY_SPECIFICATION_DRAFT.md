# Governance Authority Boundary Specification Draft

## Status

- Document status: draft for architecture review
- Version: 0.1 draft
- Identifier: not assigned
- Classification: project-governance working specification draft
- Working owner: ResearchOS project
- Decision status: not reviewed or accepted
- Formal ratification status: not defined by current repository governance
- Enforcement status: not implemented
- Recorded: 2026-07-18
- Evidence observation revision:
  `24621f3cd7348627075537cf4640625d09e6e229`
- Upstream working specification:
  `Documents/GOVERNANCE_INSTRUMENT_STATUS_AND_DECISION_BOUNDARY.md`
- Upstream Governance Baseline specification:
  `Documents/GOVERNANCE_BASELINE_SPECIFICATION.md`
- Upstream observational snapshot:
  `Documents/FIRST_GOVERNANCE_BASELINE_SNAPSHOT_DRAFT.md`

This draft defines boundaries for reasoning about authority. It does not assign,
delegate, recognize, ratify, activate, publish, or revoke governance authority.
It does not convert project-owner working-direction evidence, repository
permissions, runtime roles, review decisions, CI results, signatures, or
document labels into formal authority. It cannot approve or ratify itself.

The title is a working title. It does not create a document family, identifier
scheme, registry, lifecycle, precedence rule, or canonical instrument.

## 1. Purpose

ResearchOS contains multiple kinds of permission, review responsibility,
operational control, and project-direction evidence. These capabilities are
valid within their bounded contexts, but their names alone do not prove
governance authority.

This draft provides a common boundary for distinguishing:

- governance authority from runtime permission;
- review responsibility from decision authority;
- repository access from governance status;
- implementation authorization from activation authorization;
- evidence authenticity from decision legitimacy;
- domain-local authority from cross-domain or global authority; and
- observed project direction from formal ratification.

Its purpose is to prevent authority laundering, circular authorization, and
unattributed status claims while preserving the authority gaps recorded by the
repository.

## 2. Scope

This draft covers analytical boundaries for:

- project-owner working-direction evidence;
- governance decisions;
- architecture review and publication;
- scientific review and publication;
- repository permissions;
- runtime roles and service authorization;
- CI and release permissions;
- implementation, activation, deployment, and recovery authorization;
- attribution and decision provenance;
- delegation, succession, revocation, recusal, and appeal gaps;
- authority conflicts across bounded contexts; and
- unresolved-authority behavior.

It applies when an artifact or operation claims that a person, role, account,
service, workflow, signature, or repository action can authorize a governance
effect.

## 3. Out of Scope

This draft does not:

- identify or appoint a formal governance authority;
- define the legal or organizational basis of the project owner;
- grant the project owner formal ratification authority;
- create an authority role, registry, lifecycle, identifier, or hierarchy;
- define quorum, voting, delegation, succession, recusal, appeal, or
  conflict-of-interest procedures;
- define cross-domain precedence or exception authority;
- alter an existing runtime role or permission;
- alter an architecture, scientific, repository, review, release, deployment,
  or recovery workflow;
- issue, approve, ratify, publish, activate, supersede, or retire an
  instrument;
- change the status of an existing document;
- create enforcement, validation, persistence, APIs, or CI behavior;
- infer external GitHub settings or account ownership; or
- authorize implementation merely because this draft is reviewed or accepted
  as working direction.

## 4. Architectural Position

| Dimension | Position |
| --- | --- |
| Layer | Project Governance |
| Subsystem | Governance Authority Boundary and Traceability |
| Instrument type | Working specification draft |
| Governed subject | Claims about authority and authorization |
| Observation basis | First Governance Baseline Snapshot Draft and verified repository evidence |
| Runtime position | None |
| Persistence authority | None |
| Decision authority | None assigned |
| Enforcement authority | None |

This draft is cross-domain in analytical scope. It does not become the global
authority of any domain.

## 5. Evidence Basis

The following repository evidence supports this draft at the observation
revision:

| Evidence | Observed contribution | Limitation |
| --- | --- | --- |
| Governance Instrument Status and Decision Boundary Specification | Separates governance authority, runtime permission, review, decision, implementation, and activation | Does not assign final authority |
| Governance Baseline Specification | Defines reproducible, non-self-authorizing observation | Cannot make a normative authority decision |
| First Governance Baseline Snapshot Draft | Records authority classes, gaps, dependencies, terminology conflicts, and bounded contexts | Initial observational draft; not issued or ratified |
| Architecture Law Governance Audit | Records absent law ratification, exception, activation, and retirement authority | Architecture-law scope |
| Architecture authentication and review implementation | Proves local roles and review permissions | Runtime permission is not project governance authority |
| Knowledge authentication and evidence review implementation | Proves local scientific roles and attributed review events | Scientific admission authority is domain-local |
| Repository-evolution contracts | Separates approval evidence from execution, activation, and recovery authorization | Does not establish global governance authority |
| Deployment and recovery verification | Proves actor, rationale, signature, and trust controls | Authenticity does not prove governance legitimacy |
| GitHub workflows | Proves operational CI and release-token permissions represented in repository | External branch protection, administrators, and live assignments are not repository-evidenced |
| Root repository guidance | Provides contribution, security, and conduct guidance | Does not define a unified governance authority model |

No `CODEOWNERS` file, global authority registry, or repository-contained
contract assigning formal ratification authority was observed.

### 5.1 Repository evidence locators

The principal implementation observations can be reproduced from:

| Observation | Repository locator |
| --- | --- |
| Architecture roles and authentication | `AI-Gateway/app/architecture/authentication.py` |
| Architecture review decisions | `AI-Gateway/app/architecture/governance/review_engine.py` |
| Architecture review status | `AI-Gateway/app/architecture/models/review_status.py` |
| Knowledge roles and authentication | `AI-Gateway/app/knowledge/authentication.py` |
| Knowledge route authorization | `AI-Gateway/app/router/knowledge_dependencies.py` |
| Scientific review lifecycle | `AI-Gateway/app/knowledge/extraction/models.py` |
| Evidence admission | `AI-Gateway/app/knowledge/modeling/admission.py` |
| Repository policy approval fields | `AI-Gateway/app/architecture/repository/policy_models.py` |
| Execution-authorization separation | `AI-Gateway/app/architecture/repository/evolution_models.py` |
| Dry-run authorization separation | `AI-Gateway/app/architecture/repository/evolution_dry_run_models.py` |
| Activation-authorization separation | `AI-Gateway/app/architecture/repository/evolution_closure.py` |
| Post-verification activation separation | `AI-Gateway/app/architecture/repository/evolution_post_verification.py` |
| Evidence review persistence | `deploy/postgres/init/004_evidence_review_workflow.sql` |
| Screening decisions | `deploy/postgres/init/020_screening_decisions.sql` |
| Structured evidence reviews | `deploy/postgres/init/022_structured_evidence_reviews.sql` |
| Architecture and regression CI | `.github/workflows/architecture-quality-gates.yml` |
| Release-token permissions | `.github/workflows/release.yml` |

These locators prove repository content at the observation revision. They do
not prove live deployment state, current account assignments, or external
platform settings.

## 6. Definitions

### 6.1 Authority claim

A statement that a subject is entitled to produce a defined decision or effect
over a defined object within a defined scope.

### 6.2 Governance authority

An evidenced entitlement to make a governance decision with a stated scope and
effect. The existence and holder of formal governance authority remain
unresolved in the observed repository.

### 6.3 Permission

A technical capability to invoke an operation, access a resource, or perform a
workflow step. Permission does not by itself establish governance authority.

### 6.4 Review responsibility

An evidenced responsibility to inspect, assess, recommend, approve, or reject
an artifact within a bounded workflow. Review responsibility does not imply
authority beyond that workflow.

### 6.5 Decision authority

Authority to select and record an allowed outcome for a defined decision
class. It must not be inferred from authorship, review, execution, or access.

### 6.6 Implementation authorization

Authorization to implement an already-bounded change. It does not imply
authorization to activate the change in production or to alter governance.

### 6.7 Activation authorization

Authorization to make an implementation effective in its target operating
environment. It is distinct from design approval, implementation authorization,
deployment capability, and governance ratification.

### 6.8 Authority provenance

Evidence connecting a decision to the decision class, subject, scope,
authority basis, reviewed object, exact revision, time, outcome, rationale,
and any constraints.

### 6.9 Authority laundering

The invalid conversion of evidence from one authority class or bounded context
into a stronger or different authority claim.

### 6.10 Unresolved authority

A condition in which the repository does not provide sufficient evidence to
identify an entitled decision-maker, scope, or effect.

## 7. Core Boundary Principles

### 7.1 No self-authorization

An artifact, role, workflow, or decision record cannot establish its own
authority merely by asserting that authority.

### 7.2 Named-role insufficiency

Names such as `admin`, `reviewer`, `approver`, `publisher`, `auditor`, or
`law_admin` do not carry authority outside the contract that defines them.

### 7.3 Bounded-context isolation

Authority or permission evidenced in one bounded context cannot be reused in
another context without a separately evidenced bridge.

### 7.4 Separate decision classes

Proposal, review, approval, ratification, implementation, activation,
publication, deployment, recovery, supersession, and retirement are separate
decision classes unless an evidenced contract explicitly combines them.

### 7.5 Evidence authenticity is not legitimacy

A signed, hashed, immutable, or reproducible record can prove integrity and
attribution. It does not by itself prove that the actor was entitled to make
the recorded decision.

### 7.6 Repository action is not governance effect

Authorship, commit, merge, tag creation, workflow success, and file presence do
not by themselves approve or ratify governance.

### 7.7 Explicit scope and effect

An authority claim is incomplete unless both its scope and intended effect are
explicit.

### 7.8 Fail-closed unresolved authority

When an operation requires an authority that has not been evidenced, the
authority claim remains unresolved. This analytical rule does not itself
create runtime enforcement.

### 7.9 Historical preservation

Later authority decisions must not rewrite historical evidence of who acted,
under which claimed basis, or which authority gaps existed at the time.

## 8. Observed Authority and Permission Classes

| Class | Repository-evidenced state | Valid boundary | Unresolved boundary |
| --- | --- | --- | --- |
| Project-owner working direction | Repeated bounded decisions associated with exact drafts and pull requests | Direction for continued bounded work | Formal identity, appointment, ratification power, succession, and delegation |
| Governance authority | Need and gaps are documented | None globally assigned | Holder, basis, scope, precedence, and decision classes |
| Architecture runtime permission | Roles and fail-closed authentication exist | Architecture endpoints and workflows | Project-governance effect |
| Architecture review responsibility | Reviewer decisions and approval requirements exist | Architecture review sessions and ARC workflow | Global ratification or activation |
| Scientific review responsibility | Review events, evidence admission, and attributed decisions exist | Scientific evidence lifecycle | Project-governance effect |
| Repository permission | Git history proves repository actions occurred | Repository operation performed | Live account entitlement, branch protection, and governance effect |
| CI permission | Workflows can execute checks | Automated verification represented by workflow | Human approval or ratification |
| Release permission | Release workflow requests operational token permissions | GitHub release operation from qualifying trigger | Governance publication or production activation authority |
| Implementation authorization | Bounded project decisions and contracts distinguish implementation | Defined implementation scope | General authority to activate or change governance |
| Deployment and recovery control | Actor, rationale, signature, and trust evidence exist | Operational execution and verification | Global governance authority |
| Publication permission | Architecture, scientific, and GitHub publication concepts exist separately | Their local artifact or operation | Cross-domain publication authority |

## 9. Bounded-Context Map

| Bounded context | Representative authority or permission evidence | Prohibited inference |
| --- | --- | --- |
| Project Governance | Project-owner working-direction records | Formal ratification authority |
| Architecture | `law_admin`, `reviewer`, `approver`, `publisher`, `auditor` | Scientific, repository, or project-governance authority |
| Scientific Knowledge | `admin`, `discoverer`, `auditor`, `reviewer`, `indexer`; evidence review events | Architecture or project-governance authority |
| Repository Evolution | Approval provenance, execution and recovery flags | Production activation or global governance authority |
| GitHub Repository | Commits, merges, workflows, release permissions | Ratification, canonical status, or live administrative authority |
| Deployment and Recovery | Actor, rationale, signatures, trusted keys | Authority to create governance |
| Documentation | Authorship and repository presence | Approval, precedence, or binding status |

A shared role label across two rows is a lexical collision, not evidence of
shared authority.

## 10. Decision-Class Separation

The following transitions require independent authority evidence unless a
future valid contract explicitly and lawfully combines them:

```text
Proposal
  -> Review
  -> Governance Decision
  -> Implementation Authorization
  -> Implementation
  -> Verification
  -> Activation Authorization
  -> Activation or Publication
```

This diagram is an analytical separation, not a lifecycle. It does not require
every domain to use these labels or this sequence.

Evidence for a later action does not retroactively prove an earlier decision.
For example:

- a merge does not prove approval;
- passing tests do not prove implementation authorization;
- deployment does not prove activation authorization;
- publication does not prove ratification; and
- continued use does not prove canonical status.

## 11. Minimum Authority-Claim Record

A future authority claim should be reviewable against at least:

- decision class;
- actor or subject;
- authenticated identity evidence;
- authority basis;
- bounded context;
- scope;
- object and exact revision;
- requested and actual effect;
- decision time;
- outcome;
- rationale;
- constraints and expiry, if any;
- delegation evidence, if delegation is claimed;
- conflicts or recusal evidence, when applicable;
- supporting review and verification evidence;
- superseded or related decision references; and
- known limitations.

This section describes the evidence needed to assess a claim. It does not
create a record format, registry, signature requirement, or authority.

## 12. Project-Owner Working-Direction Boundary

The repository evidences project-owner decisions that accept exact revisions
as bounded working direction. Those records support continued drafting and
review within their stated scope.

They do not currently prove:

- formal appointment to a governance office;
- unlimited project-governance authority;
- ratification, issuance, or precedence authority;
- authority to delegate or transfer authority;
- a succession or incapacity mechanism;
- an exemption from conflict-of-interest review;
- authority to activate implementation; or
- authority to convert an observational artifact into governance truth.

Any future use of project-owner evidence must retain the exact decision,
revision, bounded effect, non-effect, and unresolved-authority statement.

## 13. Runtime Role Boundary

Runtime authentication and authorization answer whether a principal may invoke
a technical capability. They do not answer whether that principal may create
binding governance.

Accordingly:

- `law_admin` may only have the effect defined by the architecture service;
- `approver` does not become a repository-wide approval authority;
- `publisher` does not become a global publication authority;
- `reviewer` remains isolated to its architecture or scientific contract;
- `admin` does not become project owner; and
- possession of a bearer token does not prove governance entitlement.

## 14. Repository, CI, and Release Boundary

The observed repository proves that commits, merges, checks, and release
workflows can occur. It does not contain sufficient evidence to reconstruct
all live GitHub permissions or protections.

The following remain external or unresolved:

- repository administrator assignments;
- branch-protection rules;
- required reviewers;
- tag-protection rules;
- account-to-person identity;
- organization ownership;
- emergency access; and
- revocation history.

Repository or CI evidence may support provenance and verification. It must not
be promoted into authority evidence without an explicit, independently
supported authority basis.

## 15. Implementation, Activation, Deployment, and Recovery Boundary

Implementation authorization, activation authorization, deployment
capability, and recovery authorization are separate.

Observed repository-evolution contracts explicitly preserve this separation by
recording states in which approval or verification does not authorize
production activation or recovery. Deployment and recovery evidence can prove
that an actor, rationale, artifact, signature, or result was recorded. It
cannot establish the actor's global governance authority.

No future specification should collapse these boundaries solely for workflow
convenience.

## 16. Publication Boundary

ResearchOS uses publication concepts in multiple contexts:

- publication of scientific outputs;
- publication of architecture review artifacts;
- publication of a GitHub release; and
- possible future publication of governance instruments.

These are separate effects. Authority for one must not be inferred as
authority for another.

## 17. Authority-Laundering Guards

The following inferences are invalid unless separately evidenced:

| Source evidence | Invalid promoted claim |
| --- | --- |
| Document authorship | Authority to approve or ratify the document |
| Repository merge access | Governance ratification authority |
| Successful CI | Human approval or governance acceptance |
| Runtime role | Cross-domain governance authority |
| Review approval | Implementation or activation authorization |
| Project-owner working direction | Formal ratification or global precedence |
| Signed or immutable evidence | Entitlement of the signer to decide |
| Deployment success | Authorization to activate |
| Published artifact | Canonical or binding status |
| Repeated historical use | Valid issuance or ratification |

An authority claim that depends on one of these promotions must remain
unresolved until the missing bridge is evidenced.

## 18. Circular-Authority Guards

This draft cannot:

- establish the authority required to approve itself;
- use its own definitions as proof that an actor holds authority;
- treat repository acceptance as formal ratification;
- appoint the reviewer who can transform it into binding governance;
- bootstrap a global authority from a domain-local role; or
- use a future registry as retrospective proof of authority that did not exist.

The safe working dependency is:

```text
Verified authority evidence
  -> authority-boundary draft
  -> architecture review
  -> bounded external working-direction decision
  -> separately justified authority constitution or assignment
  -> implementation and verification
```

The bounded working-direction decision may authorize further work. It does not
by itself fill the formal-authority gap.

## 19. Missing Governance Analysis

The repository does not yet provide sufficient evidence for:

1. **Authority basis and identity** — who holds formal authority and why.
2. **Scope and limits** — which decisions each authority may make.
3. **Delegation and revocation** — how authority may be transferred or
   withdrawn.
4. **Succession and incapacity** — how continuity is preserved.
5. **Conflict of interest and recusal** — when a decision-maker must not act.
6. **Quorum and collective decisions** — whether and how multi-party decisions
   become valid.
7. **Review, objection, appeal, and escalation** — how contested decisions are
   handled.
8. **Cross-domain precedence** — how conflicting authority claims are resolved.
9. **Issuance, ratification, activation, publication, supersession, and
   retirement authority** — who may produce each effect.
10. **Durable decision memory** — how decisions and corrections remain
    independently reproducible.
11. **Authority registry** — whether a registry is needed and, if so, who
    governs it.
12. **External platform mapping** — how live accounts and permissions map to
    governed identities.

These are recorded gaps, not requirements created by this draft.

## 20. Dependency Boundary

The observed dependency direction is:

```text
Governance Instrument Status and Decision Boundary
  -> Governance Baseline Specification
  -> First Governance Baseline Snapshot Draft
  -> Governance Authority Evidence Review
  -> this Authority Boundary Specification Draft
```

Future normative authority construction would additionally depend on an
independent basis for the authority that reviews or adopts it. This draft does
not determine that basis.

## 21. Required Architecture Review

Before any bounded working-direction decision, review must verify:

### 21.1 Dependency verification

- upstream specifications and snapshot remain identifiable;
- cited code and workflow evidence exists at the observation revision;
- external evidence is not represented as repository-contained evidence.

### 21.2 Architecture position

- the draft remains at the Project Governance layer;
- it does not become a runtime authorization service;
- cross-domain analysis does not become cross-domain authority.

### 21.3 Contract review

- existing role names and lifecycle terms are not redefined;
- status and decision boundaries remain compatible;
- observation is not converted into a normative decision.

### 21.4 Safety review

- no self-authorization exists;
- no authority laundering exists;
- no role, registry, lifecycle, identifier, or precedence is created;
- unresolved authority remains explicit;
- decision provenance remains attributable.

### 21.5 Compatibility review

- architecture, scientific, repository, CI, release, deployment, and recovery
  permissions retain their local meanings;
- accepted working direction is not presented as formal ratification;
- historical records are not rewritten.

## 22. Acceptance Boundary

A future project-owner decision may accept an exact revision of this draft only
as bounded working direction for subsequent authority-governance work.

Such acceptance would not:

- assign formal authority;
- ratify this draft;
- make it canonical, binding, active, or precedence-bearing;
- authorize implementation;
- authorize governance issuance;
- resolve delegation, succession, recusal, appeal, or authority identity;
- change any existing document status; or
- permit this draft to approve a later authority instrument.

The decision must cite the exact reviewed revision and state both bounded effect
and non-effect.

## 23. Construction Boundary for Later Work

Later authority governance must not be constructed until:

- this draft receives an architecture review against exact evidence;
- contradictions and authority-laundering risks are reported;
- a bounded decision about continued work is recorded externally to the draft;
- the decision does not claim formal ratification without an independently
  evidenced basis; and
- any proposed assignment of formal authority is handled as a separate
  decision problem.

## 24. Unresolved Dependencies

This draft deliberately leaves unresolved:

- the formal authority model;
- the identity and basis of formal authority holders;
- authority delegation and succession;
- decision procedures and thresholds;
- conflict-of-interest, recusal, objection, and appeal;
- cross-domain precedence and exception handling;
- documentation governance;
- decision-memory governance;
- authority-registry need and ownership;
- GitHub and deployment account mapping; and
- implementation or enforcement design.

## 25. Definition of Done for This Draft

This draft is ready for architecture review when:

- authority and permission classes are explicitly separated;
- bounded contexts and lexical role collisions are recorded;
- project-owner working direction is bounded without promotion to ratification;
- repository, CI, runtime, review, publication, deployment, and recovery
  boundaries are documented;
- authority-laundering and circular-authority risks are explicit;
- minimum authority-claim evidence is described without creating a registry;
- missing governance is recorded without assigning authority;
- upstream evidence and observation revision are identified;
- no source code or runtime contract is changed;
- no role, lifecycle, identifier, registry, or enforcement is created;
- repository validation passes; and
- the document remains a non-self-authorizing draft.
