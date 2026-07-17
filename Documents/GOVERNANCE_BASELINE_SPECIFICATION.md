# Governance Baseline Specification

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
- Upstream working specification:
  `Documents/GOVERNANCE_INSTRUMENT_STATUS_AND_DECISION_BOUNDARY.md`
- Upstream revision: `8106ff6d621e0437b85be80b3bb4caf2f55a5566`

This specification defines the bounded responsibility of a future Governance
Baseline artifact. The project owner reviewed exact revision
`8ef3dca0be41361f8663392a1222c4dd6b8fed5a` and recorded a bounded
working-direction decision in pull request `#27`. This specification is not
itself a Governance Baseline, does not create the first baseline snapshot, and
does not declare itself canonical, ratified, published, active, approved as
binding governance, or precedence-bearing. Its working title does not
establish a document family, identifier convention, registry, lifecycle, or
authority.

## 1. Purpose

This specification defines how a Governance Baseline must represent a
repository-evidenced governance state as an immutable observational artifact.
It exists to make later governance work traceable to verified evidence without
allowing repository presence, document labels, or analytical conclusions to
become governance authority.

The specification separates:

- observation from decision;
- verified evidence from repository presence;
- analytical interpretation from normative interpretation;
- factual correction from governance amendment or supersession;
- historical preservation from replacement; and
- baseline facts from later specifications, decisions, implementations, and
  verification results.

## 2. Scope

This specification defines:

- the responsibility and decision boundary of a Governance Baseline;
- minimum observation metadata;
- evidence inclusion, exclusion, and verification requirements;
- fact, relationship, classification, conflict, gap, uncertainty, and
  limitation records;
- bounded-context and dependency observations;
- confidence and reproducibility requirements;
- stable content identity requirements without selecting an identifier
  format;
- historical preservation and factual correction requirements;
- material-change assessment inputs without defining a trigger or authority;
- compatibility with existing repository artifacts using the word
  `baseline`;
- review requirements for a future baseline specification decision; and
- the boundary before a first Governance Baseline Snapshot may be drafted.

## 3. Out of Scope

This specification does not:

- create a Governance Baseline Snapshot;
- assign a Governance Baseline identifier or prefix;
- create a baseline registry or storage system;
- define a document lifecycle;
- define who may issue, approve, ratify, supersede, or retire a baseline;
- define a final material-change trigger;
- classify an existing document as a Governance Baseline;
- rename or rewrite an existing baseline, audit, roadmap, or specification;
- resolve governance conflicts;
- establish governance precedence;
- authorize a Governance Specification, Authority Decision Record, or
  implementation;
- modify source code, persistence, APIs, CI, or runtime behavior; or
- convert analytical findings into normative requirements for other domains.

## 4. Architectural Position

The working architecture position is:

| Dimension | Position |
| --- | --- |
| Layer | Project Governance |
| Subsystem | Governance Observation and Traceability |
| Instrument type | Governance Specification |
| Governed artifact | Governance Baseline |
| Governed responsibility | Reproducible observation of repository-evidenced governance state |
| Runtime position | None |
| Persistence authority | None established by this specification |
| Decision authority | None established by this specification |

The Governance Baseline is cross-domain in observation scope but has no
cross-domain decision authority. It may describe evidence from Scientific,
Architecture, Engineering, Repository, Documentation, Review, Deployment, and
other evidenced bounded contexts without assuming ownership of their
lifecycle or canonical contracts.

## 5. Upstream Contract

This specification extends Section 17 of the upstream working specification.
The following upstream constraints remain controlling working boundaries:

1. a Governance Baseline is an immutable observational artifact;
2. it records a repository-evidenced governance state within an explicit
   observation boundary;
3. repository presence alone is not verified evidence;
4. analytical interpretation is permitted, but normative interpretation is
   prohibited;
5. evidence and method must support derived relationships and
   classifications;
6. historical baselines must not be overwritten;
7. correction is distinct from amendment and supersession;
8. not every repository change requires a later baseline;
9. a baseline cannot approve a specification or imply an authority decision;
   and
10. availability of an upstream artifact does not authorize the next
    activity.

If this specification conflicts with the upstream working specification, the
conflict must be reported. This specification must not silently reinterpret
the upstream contract.

## 6. Definitions

### 6.1 Governance Baseline

An immutable observational artifact that records a repository-evidenced
governance state within an explicit and reproducible observation boundary.

### 6.2 Repository-evidenced governance state

A description supported by repository evidence whose location, revision,
relevance, and verification method are recorded. Presence in the repository
does not by itself establish validity, authority, status, or current effect.

### 6.3 Observation

A statement about evidence that was inspected within the declared observation
boundary. An observation may be direct or analytically derived, but its class
must be explicit.

### 6.4 Direct observation

A statement whose content can be traced directly to identified repository
evidence without an additional analytical inference.

### 6.5 Derived observation

A reproducible relationship, classification, conflict, gap, or other
analytical conclusion produced from identified evidence using a stated
method.

### 6.6 Normative interpretation

A statement that prescribes what must be done, establishes authority,
precedence, status, lifecycle, obligation, permission, or prohibition, or
authorizes implementation. A Governance Baseline must not make such a
statement.

### 6.7 Observation boundary

The repository revision, time, evidence scope, exclusions, method,
limitations, and unresolved conflicts that bound what the baseline can claim.

### 6.8 Factual correction

A traceable repair to the representation of observed evidence. It preserves
the original artifact and does not change governance authority or normative
effect.

### 6.9 Material-change assessment

An analytical assessment of whether later repository evidence may materially
affect a previous governance observation. It is not, by itself, authorization
to issue another baseline.

## 7. Core Principles

### 7.1 Observational artifact principle

A Governance Baseline records what was observed and supported by verified
repository evidence. It does not decide what ought to govern ResearchOS.

### 7.2 No self-authorization principle

Neither the baseline nor this specification may establish its own authority,
ratification, canonical status, precedence, or binding effect.

### 7.3 Evidence-before-claim principle

Every factual or analytical claim must identify supporting evidence. An
unsupported claim must be excluded or recorded explicitly as unresolved.

### 7.4 Reproducibility principle

Another reviewer using the recorded repository revision, scope, evidence
references, and method must be able to reconstruct the basis of an
observation.

### 7.5 Historical preservation principle

A published historical observation must not be silently edited to represent a
later state or repair an error.

### 7.6 Domain isolation principle

Observation across bounded contexts does not transfer lifecycle, terminology,
authority, or canonical ownership from one domain to another.

### 7.7 Explicit uncertainty principle

Conflicting, incomplete, stale, or ambiguous evidence must reduce confidence
or remain unresolved. It must not be resolved through assumption.

### 7.8 Stable identity principle

The content and observation boundary must have a stable identity sufficient to
distinguish exact baseline contents. This specification does not select the
identity algorithm, identifier syntax, or registry.

## 8. Required Observation Record

A Governance Baseline must record at least:

| Field | Required meaning |
| --- | --- |
| Repository revision | Exact revision used for observation |
| Observation timestamp | Time at which the repository state was observed |
| Included evidence scope | Paths, artifact classes, or other bounded inclusion criteria |
| Excluded scope | Evidence deliberately outside the observation |
| Verification method | Reproducible inspection and analytical methods |
| Known limitations | Constraints affecting completeness or interpretation |
| Unresolved conflicts | Conflicting evidence not resolved by assumption |
| Confidence basis | Evidence-based reason for confidence assigned to findings |
| Predecessor reference | Earlier baseline, when one exists |
| Correction reference | Related correction record, when one exists |
| Stable content identity | Identity of the exact content and observation boundary |

The record must also disclose:

- the purpose of the observation;
- the bounded contexts inspected;
- the evidence-selection method;
- verification failures or inaccessible evidence;
- historical, draft, fixture, generated, or example content that could be
  mistaken for current governance;
- the analysis method for derived observations; and
- the absence of a predecessor or correction when those fields do not apply.

The future baseline format may organize these fields differently, but it must
preserve their meaning and traceability.

## 9. Evidence Admission

### 9.1 Inclusion requirements

Evidence may support a baseline claim only when:

- its repository location is identified;
- the observed revision is fixed;
- its relationship to the claim is explained;
- its artifact type and apparent status are recorded;
- relevant authority evidence is distinguished from status text;
- relevant implementation claims are checked against canonical code,
  persistence contracts, tests, or verification evidence where applicable;
  and
- conflicts or limitations are disclosed.

### 9.2 Repository presence is insufficient

The following require explicit qualification and must not be treated as
current governance merely because they exist:

- drafts;
- historical documents;
- superseded records;
- fixtures and examples;
- generated output;
- roadmap intent;
- comments and prose unsupported by implementation evidence;
- status labels without decision evidence; and
- domain-specific lifecycle terms used outside their bounded context.

### 9.3 Exclusion record

Material evidence excluded from the observation must be recorded with:

- its location or selection class;
- the reason for exclusion; and
- the expected impact of the exclusion on completeness or confidence.

### 9.4 Conflicting evidence

When evidence conflicts, the baseline must:

1. preserve references to each relevant source;
2. describe the conflict without selecting a normative winner;
3. distinguish factual inconsistency from governance disagreement;
4. state the analytical effect on findings and confidence; and
5. leave authority-dependent resolution unresolved.

## 10. Observation Classes

Every substantive finding must be distinguishable as one of:

| Class | Meaning |
| --- | --- |
| Observed fact | Directly supported by identified repository evidence |
| Derived relationship | Reproducible relationship inferred from multiple evidence items |
| Analytical classification | Evidence-based categorization using a stated method |
| Conflict finding | Incompatible or divergent evidence |
| Governance gap | An expected governance dependency not evidenced in scope |
| Uncertainty | A claim whose support is incomplete or ambiguous |
| Evidence limitation | A boundary that restricts completeness or confidence |
| Excluded or unverified claim | A repository claim not admitted as verified evidence |

Classification does not create status or authority. A `governance gap`, for
example, is an observed absence within scope, not authorization to fill it.

## 11. Bounded-Context Mapping

When a baseline maps governance evidence, it must:

- identify the bounded context supported by repository evidence;
- identify local terminology and lifecycle ownership;
- distinguish local, cross-domain, and apparently global effects;
- distinguish runtime authority from governance authority;
- identify canonical implementation or persistence ownership where evidenced;
- record cross-context dependencies without merging their lifecycles; and
- record uncertain ownership as unresolved.

A mapping must not invent a bounded context merely to simplify the analysis.
It must state the evidence and method used to establish each boundary.

## 12. Dependency Analysis

A dependency claim must record:

- upstream governance or evidence;
- downstream consumer;
- the evidence establishing the dependency;
- the dependency type;
- the direction of dependency;
- any unresolved authority or compatibility constraint; and
- the confidence basis.

The baseline must detect and report apparent circular dependencies. It must
not resolve a cycle by assigning authority or precedence.

Dependency analysis may describe:

- evidentiary dependency;
- specification dependency;
- decision dependency;
- implementation dependency;
- verification dependency;
- documentation dependency; or
- operational dependency.

These analytical labels do not create a global dependency taxonomy outside the
baseline observation.

## 13. Confidence and Limitations

Confidence must be explained, not merely scored. The basis should consider:

- directness of evidence;
- consistency across evidence sources;
- revision stability;
- authority traceability;
- implementation and verification support;
- bounded-context clarity;
- known omissions; and
- unresolved conflict.

This specification does not require a numeric confidence scale. A future
baseline may use qualitative or quantitative representation only when the
method and meaning are explicit.

Limitations must be visible near affected findings or linked from them. A
global limitation statement must not conceal a finding-specific weakness.

## 14. Reproducibility and Stable Content Identity

The observation must be reproducible from a fixed repository revision.
Evidence references must be sufficiently precise to locate the observed
material at that revision.

The stable content identity must be derived from an identity-bearing
representation that covers:

- the baseline content;
- the observation boundary;
- evidence references;
- methods;
- limitations;
- unresolved conflicts; and
- correction or predecessor references.

The identity value itself must be excluded from the representation used to
derive that identity, so the contract does not become self-referential. The
identity must change when any other identity-bearing content changes. This
draft does not choose hashing, signing, naming, serialization, or storage
technology.

The required observation timestamp is substantive observation-boundary
content and must remain identity-bearing. A separate artifact-generation
timestamp, presentation-only formatting, or transport metadata must not make
otherwise identical observation content appear substantively different unless
the selected future identity contract explicitly includes it.

## 15. Historical Preservation and Correction

### 15.1 Immutability

Once a Governance Baseline has been assigned its stable content identity, its
identity-bearing content must not be overwritten to:

- incorporate later repository changes;
- change an analytical conclusion;
- repair a factual error silently;
- alter its scope;
- add authority evidence; or
- update its status.

### 15.2 Correction record

A factual correction must identify:

- the original baseline;
- the exact claim or evidence representation found to be incorrect;
- evidence demonstrating the error;
- the correction made;
- the impact on dependent observations;
- the corrected baseline; and
- the relationship between original, correction, and corrected artifact.

### 15.3 Boundary from supersession

A correction repairs an observation. Supersession or amendment changes
governance direction or normative effect. A Governance Baseline cannot perform
the latter and must not describe a factual correction as governance
supersession.

The authority, status, and format for a correction record remain unresolved.
This specification defines only the traceability boundary required to preserve
history.

## 16. Material-Change Assessment Boundary

Later evidence may justify considering a new baseline when it materially
affects:

- governance evidence;
- authority evidence;
- dependency relationships;
- lifecycle contracts;
- bounded-context positioning;
- canonical ownership;
- conflict resolution; or
- a previous analytical conclusion.

An assessment must compare the later evidence with the prior observation
boundary and explain the effect. It must not infer that a new baseline is
required solely because a repository revision changed.

This specification deliberately leaves unresolved:

- the final materiality criteria;
- who performs or approves the assessment;
- who may issue a later baseline;
- whether review is mandatory;
- the status of a later baseline; and
- any registry or notification requirement.

These dependencies require later governance and must not be filled by local
convention.

## 17. Separation of Artifact Responsibilities

```text
Audit Evidence
  -> supplies verified observations

Governance Baseline
  -> consolidates repository-evidenced state

Governance Specification
  -> defines normative interpretation and constraints

Authority Decision Record
  -> records a decision by evidenced authority

Implementation Authorization
  -> permits bounded implementation work

Implementation
  -> realizes the authorized decision

Verification Evidence
  -> records observed implementation results
```

Required boundaries:

- audit evidence does not become a decision;
- a baseline does not approve a specification;
- a specification does not rewrite a historical baseline;
- an authority decision is not inferred from repository presence;
- a decision does not imply implementation completion;
- implementation does not prove governance compliance by itself; and
- verification evidence does not retroactively authorize implementation.

## 18. Compatibility With Existing Baseline-Labeled Artifacts

ResearchOS already contains artifacts using the term `baseline` for different
responsibilities, including:

- File Management Architecture completion and safety evidence;
- maintenance implementation audit and roadmap evidence; and
- staged One File -- One Architectural Responsibility audit evidence.

This specification does not:

- reclassify those artifacts as Governance Baselines;
- invalidate their local meaning;
- change their acceptance or enforcement status;
- impose this specification retroactively;
- rename them; or
- infer a shared lifecycle or authority from the shared word `baseline`.

A future inventory may evaluate whether an artifact satisfies this
specification, but classification requires explicit evidence and a separate
bounded decision. Compatibility must be achieved through qualification, not
historical rewriting.

## 19. Safety Review

The specification must fail closed against:

- self-ratification;
- status derived from labels alone;
- hidden authority assignment;
- lifecycle borrowing across domains;
- silent conflict resolution;
- mutable historical evidence;
- untraceable corrections;
- baseline creation triggered by every commit;
- implementation authorization inferred from observation;
- duplicate canonical ownership; and
- conversion of repository intent into implementation truth.

No direct service, documentation shortcut, or repository convention may use a
Governance Baseline to bypass an applicable authority or implementation
boundary.

## 20. Review Requirements

Review of an exact revision of this specification must verify:

### 20.1 Dependency verification

- the upstream working specification is identified;
- Section 17 constraints are preserved;
- repository baseline terminology has been inventoried; and
- no missing authority is supplied through assumption.

### 20.2 Architecture position

- Project Governance ownership is explicit;
- observation and traceability remain separate from decision authority;
- cross-domain observation does not become cross-domain control; and
- runtime and persistence authority remain unchanged.

### 20.3 Contract review

- minimum metadata is complete;
- evidence admission is reproducible;
- analytical and normative interpretation remain separated;
- correction preserves history;
- material-change authority remains unresolved; and
- artifact responsibilities remain distinct.

### 20.4 Compatibility review

- existing baseline-labeled artifacts retain their local meaning;
- no document identifier family is created;
- no lifecycle or registry is introduced;
- no existing status is elevated; and
- canonical code and persistence contracts remain authoritative for
  implementation claims.

### 20.5 Safety review

- no self-authorization path exists;
- no baseline can authorize a specification or implementation;
- stale or conflicting evidence is visible;
- provenance remains complete; and
- correction and supersession cannot be conflated.

## 21. Acceptance Boundary

An affirmative bounded working-direction decision about this specification
would mean only that it may guide:

- Architecture Review of the baseline contract;
- later preparation of a first Governance Baseline Snapshot; and
- later governance analysis that depends on reproducible repository
  observation.

It would not:

- formally ratify this specification;
- make it globally binding;
- create authority;
- create a Governance Baseline;
- approve the contents of a future snapshot;
- select an identifier, format, registry, or storage location;
- define a lifecycle;
- resolve material-change governance;
- authorize implementation; or
- approve any later governance instrument.

## 22. Boundary Before the First Snapshot

The working bootstrap direction remains:

```text
Stage 0-2 Audit Evidence
  -> Governance Instrument Status and Decision Boundary Specification
      -> Governance Baseline Specification Draft
          -> review of an exact repository revision
              -> separate bounded working-direction decision
                  -> First Governance Baseline Snapshot
```

This dependency sequence is not a lifecycle. Completion or acceptance of this
draft does not authorize creation of the first snapshot. The snapshot requires
a separate explicit instruction after review of the exact specification
revision.

Before snapshot work begins, the review record must preserve:

- the exact specification revision;
- the bounded effect and non-effect;
- unresolved authority and format dependencies;
- compatibility findings;
- evidence used for review; and
- reconsideration conditions.

## 23. Unresolved Dependencies

The following remain intentionally unresolved:

- formal governance authority;
- ratification authority;
- documentation governance;
- cross-governance precedence;
- baseline issuance authority;
- correction-record authority and status;
- material-change criteria and decision authority;
- identifier and version convention;
- format and serialization;
- registry and storage location;
- publication and access rules;
- review and closure requirements;
- long-term retention; and
- automated validation or enforcement.

Their absence is a documented boundary, not permission for this specification
to define them indirectly.

## 24. Definition of Done for This Specification

This specification satisfied its bounded exact-revision review when:

1. upstream dependencies are explicit;
2. observational and decision responsibilities are separated;
3. required observation metadata is complete;
4. evidence admission and exclusion are reproducible;
5. analytical content is allowed without normative interpretation;
6. bounded-context and dependency analysis preserve domain isolation;
7. confidence, limitations, and conflict handling are explicit;
8. historical preservation and factual correction are traceable;
9. material-change authority remains unresolved;
10. existing baseline-labeled artifacts remain compatible;
11. no identifier, registry, lifecycle, authority, or snapshot is created;
12. no source code or runtime contract is changed;
13. repository checks report no formatting error; and
14. the exact revision is available for a separate bounded project-owner
    decision.

The reviewed revision and decision evidence are recorded in Section 25.

## 25. Durable Working-Direction Decision Record

### 25.1 Decision

- Instrument: `Governance Baseline Specification`
- Reviewed version: `0.1 draft`
- Instrument location:
  `Documents/GOVERNANCE_BASELINE_SPECIFICATION.md`
- Claim class: working-direction claim
- Decision maker: ResearchOS project owner
- Authority basis: existing project-owner authority consistently recorded by
  ResearchOS vision, governance, roadmap, architecture, and engineering
  documents
- Reviewed revision: `8ef3dca0be41361f8663392a1222c4dd6b8fed5a`
- Decision date: 2026-07-18
- Architecture Review evidence:
  `https://github.com/jumadi03/ResearchOS/pull/27#issuecomment-5007050298`
- Decision evidence:
  `https://github.com/jumadi03/ResearchOS/pull/27#issuecomment-5007064507`
- Scope: Governance Baseline specification and analysis

### 25.2 Bounded effect

The specification may guide:

- later governance analysis;
- Architecture Review of Governance Baseline artifacts;
- specification work that depends on reproducible repository observation; and
- preparation planning for a separately authorized First Governance Baseline
  Snapshot.

### 25.3 Non-effect

This decision does not:

- formally ratify the specification;
- make it canonical, globally binding, or precedence-bearing;
- create a Governance Baseline;
- authorize the First Governance Baseline Snapshot;
- create an identifier, registry, lifecycle, authority, publication rule, or
  enforcement mechanism;
- resolve material-change criteria, issuance authority, correction authority,
  or documentation governance;
- authorize source-code, runtime, persistence, or implementation changes; or
- approve any later governance instrument or artifact.

### 25.4 Supporting evidence

- Stage 0 Dependency Verification and Phase Inventory;
- Stage 1 Governance Architecture Review;
- Stage 2 Governance Consolidation Review;
- the upstream Governance Instrument Status and Decision Boundary
  Specification;
- the exact revision reviewed by the project owner;
- the durable Architecture Review record;
- the durable project-owner decision record; and
- six successful Architecture Quality Gate jobs for the reviewed revision.

### 25.5 Unresolved dependencies

All dependencies in Section 23 remain unresolved. This decision does not
reduce, replace, or implicitly satisfy them.

### 25.6 Reconsideration condition

This working-direction decision must be reviewed if a later authority model,
documentation-governance specification, or conflicting higher-scope
governance instrument is accepted.
