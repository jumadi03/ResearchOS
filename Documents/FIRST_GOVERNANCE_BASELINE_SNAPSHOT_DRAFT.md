# First Governance Baseline Snapshot Draft

## 1. Observation Metadata

| Field | Observed value |
| --- | --- |
| Working title | First Governance Baseline Snapshot Draft |
| Document status | initial observational snapshot draft |
| Instrument type | observational artifact draft |
| Observation timestamp | `2026-07-17T20:32:00Z` |
| Exact repository revision | `c0957d233aa3da0a74b849c639b0506654c1f929` |
| Observed branch | `main` |
| Predecessor | not applicable |
| Correction reference | not applicable |
| Stable content identity | `0d27b75e81cc7c03a06cff1750ea97619fb2148a47264bda44c0bc3356b4c5b4` |
| Identity algorithm | SHA-256 |
| Identity representation | Markdown UTF-8, LF line endings |
| Identity scope | Entire file after replacing the stable-content-identity value with the literal sentinel `IDENTITY_EXCLUDED_FROM_HASH` |
| Authority effect | none |
| Issuance status | not issued |
| Ratification status | not ratified |
| Canonical status | not claimed |
| Binding effect | none |

This file is an initial observational snapshot draft. It is not an issued,
canonical, ratified, approved, active, published, binding, authoritative, or
completed Governance Baseline. It does not create a governance identifier,
registry, lifecycle, authority, precedence rule, implementation
authorization, or activation decision.

### 1.1 Included scope

The observation includes tracked repository evidence at the exact revision:

- all 26 Markdown documents under `Documents/`;
- root project and community artifacts: `README.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `CITATION.cff`, `LICENSE`,
  and `NOTICE`;
- governance-relevant source under `AI-Gateway/app/architecture/`,
  `AI-Gateway/app/knowledge/`, `AI-Gateway/app/runtime/`, product and router
  authentication boundaries, and their public models;
- tests under `AI-Gateway/app/`, including architecture, knowledge, product,
  runtime, persistence, deployment-contract, and recovery tests;
- 32 SQL migrations under `deploy/postgres/init/`;
- 18 verifier artifacts under `deploy/verify/`;
- `.github/workflows/architecture-quality-gates.yml` and
  `.github/workflows/release.yml`;
- deployment, backup, restore, monitoring, and migration definitions where
  they provide governance or control evidence; and
- the tracked tree, file paths, Git history reachable from the observed
  revision, and internal cross-references.

The observed tree contains 510 tracked files, including 357 Python files under
`AI-Gateway/app/`, 85 test files under that application tree, 32 PostgreSQL
migrations, 18 deployment verifiers, and 2 workflow definitions.

### 1.2 Excluded scope

The observation excludes:

- every repository state after the exact revision;
- this snapshot draft itself, because it does not exist at the observed
  revision;
- untracked files, local modifications, caches, temporary directories,
  virtual environments, and generated test output;
- credentials, local access files, tokens, and environment-specific secrets;
- live PostgreSQL, MinIO, worker, browser, network, and deployment state;
- GitHub branch protection, repository settings, permission assignments,
  issue state, PR state, comments, and Actions results except where a tracked
  artifact records a URL or claim about them;
- external scientific sources and provider responses;
- operating-system state and local service configuration not committed at the
  revision; and
- conversation memory, conversation summaries, and Stage 0--2 claims that
  cannot be reconstructed from the repository.

These exclusions prevent claims about live operational compliance, current
external permissions, or external decision content.

### 1.3 Verification method

Evidence was read from the Git object identified by the exact revision. The
method used:

1. exact revision and ancestor verification;
2. tracked-tree enumeration;
3. document status, authority, scope, dependency, and limitation inspection;
4. source inspection of enums, constructors, guards, services, roles, and
   serialization;
5. test inspection for exercised boundaries;
6. SQL inspection for persistence constraints, canonical ownership,
   immutability, and lifecycle states;
7. CI workflow inspection for declared quality gates;
8. deployment and recovery verifier inventory;
9. internal cross-reference verification;
10. bounded-context classification;
11. authority and lifecycle isolation review;
12. conflict, ambiguity, gap, and circular-dependency review; and
13. local content-identity reproduction after the document was finalized.

No documentation statement was accepted as implementation truth when source
code or persistence contracts supplied the relevant canonical evidence.

### 1.4 Content identity method

The local method applies only to this first snapshot draft:

1. read the file as UTF-8 without a byte-order mark;
2. normalize all line endings to LF;
3. replace the value between backticks in the metadata row
   `Stable content identity` with the literal
   `IDENTITY_EXCLUDED_FROM_HASH`;
4. retain the observation timestamp and every other identity-bearing field;
5. encode the resulting text as UTF-8;
6. calculate SHA-256 over those bytes; and
7. compare the lowercase hexadecimal result with the reported file hash.

The stored identity value is excluded to prevent self-reference. The
observation timestamp remains identity-bearing. This method is not a global
format, repository standard, registry contract, identifier convention, or
precedent for later snapshots.

### 1.5 Known limitations

- Stage 0, Stage 1, and Stage 2 are named as evidence bases in the two working
  specifications, but their complete reports are not independent repository
  artifacts at the observed revision.
- GitHub decision and Architecture Review records are represented by URLs in
  tracked documents; their external content is not reproducible offline from
  the Git tree.
- Workflow definitions are repository evidence, but this snapshot does not
  observe live Actions execution or branch-protection configuration.
- Persistence definitions and verifiers are observable; live database and
  object-store state are excluded.
- Document status headers are claims whose authority effect must be evaluated
  separately from their text.
- Some governance-bearing documents use historical wording such as
  `this draft` after their status header was changed to a working
  specification.
- The repository does not define global documentation governance,
  cross-governance precedence, baseline issuance authority, or a global
  governance registry.

### 1.6 Unresolved conflicts

- `project-owner-accepted` and `Authority: project owner` appear across
  documents while formal ratification authority remains undefined.
- `approved`, `accepted`, `verified`, `completed`, `published`, `active`,
  `closed`, `archived`, and `ratified` have bounded-context-specific meanings
  and no evidenced global equivalence.
- `baseline` labels several local audit or completion artifacts that are not
  Governance Baselines under the working specification.
- The working specifications depend on Stage 0--2 audit evidence whose
  detailed reports are not stored independently in the repository.
- External decision URLs improve traceability but do not provide complete
  offline reproducibility.

### 1.7 Confidence basis

Confidence labels in this snapshot are analytical, not governance statuses:

- **High**: direct evidence from a fixed Git revision, reinforced by source,
  persistence, or tests.
- **Moderate**: direct document evidence with incomplete external authority,
  live-state, or independent decision evidence.
- **Limited**: absence or relationship inferred from the bounded repository
  search, materially affected by excluded external state.

## 2. Observation Method and Evidence Classes

### 2.1 Evidence classes

| Class | Meaning in this snapshot |
| --- | --- |
| Repository fact | Directly visible in a tracked artifact at the exact revision |
| Analytical classification | Reproducible interpretation derived from identified repository facts |
| Unresolved ambiguity | Evidence supports more than one interpretation and no authority resolves it |
| Conflict | Repository evidence or terminology is incompatible across scopes |
| Gap | Expected governance dependency is not evidenced in the included scope |
| Limitation | The observation boundary prevents a stronger conclusion |
| External evidence reference | A tracked URL or reference whose target is outside the Git tree |

Classification does not grant status, authority, precedence, or normative
effect.

### 2.2 Evidence admission

A claim was admitted only when its tracked location and relationship to the
finding were identifiable. Drafts, roadmaps, examples, fixtures, generated
artifacts, test identities, and status labels were qualified by their local
role. Runtime roles were treated as operational permissions, not governance
authority. Source and SQL contracts were preferred for implementation claims.

### 2.3 Reconstruction boundary for Stage 0--2

Repository facts:

- `Documents/GOVERNANCE_INSTRUMENT_STATUS_AND_DECISION_BOUNDARY.md` names
  Stage 0 Dependency Verification and Phase Inventory, Stage 1 Governance
  Architecture Review, and Stage 2 Governance Consolidation Review as its
  evidence basis.
- `Documents/GOVERNANCE_BASELINE_SPECIFICATION.md` names those stages as
  supporting evidence and as the beginning of its bootstrap dependency.
- no standalone Stage 0, Stage 1, or Stage 2 report is present under
  `Documents/` at the exact revision.

Analytical finding, confidence **High**: Stage 0--2 can identify review areas,
but their detailed findings cannot be imported as repository facts. This
snapshot reconstructs its observations directly from the repository.

## 3. Governance Bootstrap Evidence

### 3.1 Governance Instrument Status and Decision Boundary Specification

| Attribute | Observation |
| --- | --- |
| Location | `Documents/GOVERNANCE_INSTRUMENT_STATUS_AND_DECISION_BOUNDARY.md` |
| Stated status | project-owner-accepted working specification |
| Identifier | not assigned |
| Decision status | accepted as bounded working direction |
| Formal ratification | not defined by current repository governance |
| Enforcement | not implemented |
| Reviewed draft revision | `a113a23b4edea2f0540d562c9d42d47c3fe30f61` |
| Durable decision reference | PR `#26`, comment URL recorded in Section 18 |
| Primary boundary | status claims, authority separation, and no self-authorization |

Repository facts:

- Section 6 separates status text from status proof and prohibits
  self-authorization.
- Section 7 distinguishes draft, working-direction, evidence-result,
  binding-governance, and historical claims.
- Section 10 says architecture runtime roles do not prove authority to ratify
  governance instruments.
- Section 13 rejects circular authority.
- Section 17 defines Governance Baseline as an immutable observational
  artifact and separates it from specifications, decisions, implementation,
  and verification.
- Section 18 records a bounded working-direction decision and explicitly
  denies ratification, global precedence, authority creation, and later
  deliverable approval.

Authority evidence: the file contains a project-owner decision record and an
external PR URL. The decision content is partly represented in the tracked
file; the external record itself is excluded.

Analytical classification, confidence **Moderate**: this is an accepted
working specification with bounded project direction, not formally ratified
global governance. Its status is reproducible; the full external decision is
not.

### 3.2 Governance Baseline Specification

| Attribute | Observation |
| --- | --- |
| Location | `Documents/GOVERNANCE_BASELINE_SPECIFICATION.md` |
| Stated status | project-owner-accepted working specification |
| Identifier | not assigned |
| Decision status | accepted as bounded working direction |
| Formal ratification | not defined by current repository governance |
| Enforcement | not implemented |
| Reviewed draft revision | `8ef3dca0be41361f8663392a1222c4dd6b8fed5a` |
| Architecture Review reference | PR `#27`, review-comment URL in Section 25 |
| Durable decision reference | PR `#27`, decision-comment URL in Section 25 |
| Primary boundary | reproducible observation without decision authority |

Repository facts:

- Sections 7--10 define observational responsibility, metadata, evidence
  admission, and observation classes.
- Sections 11--13 govern analytical mapping, dependency analysis, confidence,
  and limitations.
- Sections 14--16 define local identity constraints, immutability, correction,
  and material-change boundaries without selecting global mechanisms.
- Section 17 separates audit, baseline, specification, authority decision,
  implementation, and verification.
- Section 18 prevents reclassification of existing baseline-labelled
  artifacts.
- Sections 21--23 preserve non-effect and unresolved dependencies.
- Section 25 records bounded effect and explicitly denies snapshot
  authorization, issuance authority, registry, lifecycle, ratification, and
  implementation changes.

Authority evidence: the file records the project-owner working-direction
decision and external URLs; no formal issuance or ratification authority is
defined.

Analytical classification, confidence **Moderate**: the specification supplies
a traceable construction boundary for this draft but cannot issue or approve
the snapshot.

### 3.3 Bootstrap dependency

Declared dependency:

```text
Stage 0--2 audit areas
  -> status and decision boundary working specification
      -> Governance Baseline working specification
          -> separately authorized snapshot construction
```

Observed completion evidence:

- both specifications exist at the exact revision;
- both record exact reviewed revisions and bounded project-owner decisions;
- the Governance Baseline specification records that its decision does not
  authorize the first snapshot;
- this draft's construction authorization is external to the exact observed
  revision and therefore is not a fact inside this snapshot.

Analytical finding, confidence **High**: the repository-side bootstrap chain
through the working specifications is present. Snapshot issuance remains
outside the chain and unresolved.

### 3.4 Non-self-authorization

This snapshot:

- does not approve either specification;
- does not use its observations to create authority;
- does not convert a working-direction claim into formal ratification;
- does not assign itself an identifier or issuance status; and
- does not treat construction permission as publication or activation.

## 4. Project Direction Evidence

### 4.1 Project-direction matrix

| Artifact | Stated status | Scope | Claimed authority | Observed role | Dependency and limitation |
| --- | --- | --- | --- | --- | --- |
| `Documents/RESEARCHOS_VISION.md` | project-owner-accepted vision | long-term identity, principles, and success criteria | project owner | working project direction | formal ratification undefined; depends on no evidenced global documentation governance |
| `Documents/RESPONSIBLE_EVOLUTION_VISION.md` | project-owner-accepted governing vision | human-governed system evolution | project owner | working cross-domain direction | governance decision memory and later standards remain incomplete |
| `Documents/AUTONOMOUS_INTELLIGENCE_ROADMAP.md` | project-owner-accepted strategic direction | provider independence and native scientific intelligence | project owner | strategic sequencing guide | roadmap intent does not prove implementation or activation |
| `Documents/LONG_TERM_ENGINEERING_CHARTER.md` | project-owner-accepted maintenance charter | all layers, data, operations, documentation, and engineering work | project owner | working engineering discipline | formal ratification and repository-wide enforcement undefined |

Repository facts:

- each artifact has a status header, owner, scope, and authority claim;
- each explicitly says formal ratification status is not defined;
- the vision prohibits machine authority from ratifying evidence or bypassing
  human governance;
- the Responsible Evolution Vision separates observation, diagnosis,
  proposal, simulation, verification, and human decision;
- the roadmap is future direction and uses phased sequencing;
- the charter states that strong labels such as canonical, complete,
  ratified, and production-ready require evidence.

Analytical classification, confidence **Moderate**: these artifacts form a
coherent working project-direction layer. They are stronger than informal
notes because they record project-owner acceptance, but weaker than formally
ratified global governance because the authority and documentation framework
for that status is absent.

## 5. Domain Governance Evidence

### 5.1 Domain-governance matrix

| Artifact or family | Bounded context | Instrument type | Status claim | Enforcement and implementation relationship | Unresolved gap |
| --- | --- | --- | --- | --- | --- |
| `Documents/SCIENTIFIC_GOVERNANCE_FRAMEWORK.md` | Scientific | framework vision | project-owner-accepted framework vision | scientific contracts are partly enforced by knowledge code and PostgreSQL; framework children remain planned | formal status and child-standard ratification |
| `Documents/ARCHITECTURE_GOVERNANCE.md` plus `AI-Gateway/app/architecture/` | Architecture | operational architecture governance | purpose document without project-governance status header | deterministic graph, laws, compliance, review, ARC, APIs, roles, persistence, and tests exist | law-bundle ratification authority and global governance effect |
| `Documents/ARCHITECTURE_LAW_GOVERNANCE_AUDIT.md` | Architecture | governance audit and formalization roadmap | governance audit draft; not ratified | documentation-only; explicitly no new law, validator, registry, or lifecycle | proposer, reviewer, ratifier, exception, precedence, and activation authority |
| `Documents/FILE_MANAGEMENT_ARCHITECTURE.md` plus repository-management code | Repository | working architecture and capabilities | project-owner-accepted working architecture | repository inventory, policy, health, traceability, evolution, recovery, dashboard, and tests exist | production mutation and global file-law activation remain prohibited or undefined |
| `Documents/INTERNET_DISCOVERY_ROADMAP.md` plus discovery implementation | Scientific Discovery | implementation roadmap | project-owner-accepted working roadmap | multiple SCAN capabilities are recorded complete and backed by source, SQL, tests, and verifiers | roadmap governance and formal publication status |

### 5.2 Scientific governance

Repository facts:

- `Documents/SCIENTIFIC_GOVERNANCE_FRAMEWORK.md` uses identifier `SGF-000`
  and plans child standards SGF-010 through SGF-100.
- it calls itself a project-owner-accepted framework vision and says formal
  ratification is not defined.
- `deploy/postgres/init/003_canonical_scientific_data.sql` constrains the
  scientific artifact lifecycle to planned, draft, review, validated,
  ratified, published, deprecated, and archived.
- `AI-Gateway/app/knowledge/extraction/models.py` defines extraction review as
  provisional, accepted, or rejected.
- `AI-Gateway/app/knowledge/theory/models.py` defines theory review separately.
- source and tests reject unaccepted evidence from graph and theory paths.

Analytical finding, confidence **High** for implementation and **Moderate** for
framework status: scientific governance has operative domain controls, but
the framework's global normative status and complete standard family are not
evidenced as ratified.

### 5.3 Architecture governance

Repository facts:

- architecture governance source includes law resolution, validator registry,
  compliance, immutable review sessions, ARC generation, and publishing;
- `AI-Gateway/app/architecture/authentication.py` defines scanner, law_admin,
  reviewer, approver, publisher, and auditor runtime roles;
- review status and decisions are modeled and tested;
- ARC generation requires an approved Architecture Review;
- architecture tests exercise graph, law, compliance, review, API,
  persistence, registry, repository, and compatibility behavior;
- the Architecture Law audit explicitly states that existing runtime names do
  not prove formal law-ratification authority.

Analytical finding, confidence **High**: executable architecture governance is
operational in its software bounded context. It does not establish global
governance-instrument authority.

### 5.4 Repository governance

Repository facts:

- File Management Architecture positions repository management under the
  Architecture Governance Layer and Architecture Engine;
- source modules implement classification, policy registry, file registry,
  health, traceability, evolution planning, preflight, dry run, isolated
  execution, recovery, post-verification, closure, dashboard, and storage;
- tests repeatedly assert that reports and closure evidence do not authorize
  production activation;
- the File Management Safety Baseline prohibits production repository
  mutation at its recorded baseline.

Analytical finding, confidence **High**: repository observation and guarded
evolution capabilities exist; production activation authority is deliberately
not inferred.

### 5.5 Discovery governance

Repository facts:

- the Internet Discovery Roadmap records a P0 Evidence-to-Theory gate and
  SCAN-001A through later capability work;
- discovery and knowledge source trees contain contract, registry, query,
  inspection, screening, extraction, review, monitoring, and persistence
  implementations;
- migrations 017 through 028 supply capture, inspection, decision,
  extraction, review, intake, citation, and monitoring persistence;
- verifiers exercise source inspection, screening decision, evidence,
  canonical graph, semantic index, publication, and monitoring behavior.

Analytical finding, confidence **High** for implementation presence and
**Moderate** for roadmap governance status: the discovery pipeline is
substantially implemented, while roadmap governance remains a working
direction rather than formal global governance.

## 6. Implementation Evidence

### 6.1 Canonical lifecycle and transition evidence

| Context | Evidence | Observed states or boundary |
| --- | --- | --- |
| Scientific artifact | `deploy/postgres/init/003_canonical_scientific_data.sql` | planned, draft, review, validated, ratified, published, deprecated, archived |
| Evidence extraction review | `AI-Gateway/app/knowledge/extraction/models.py` | provisional, accepted, rejected |
| PostgreSQL evidence state | `AI-Gateway/app/knowledge/repositories/postgres_evidence.py` | provisional maps to pending; accepted and rejected retain names |
| Theory review | `AI-Gateway/app/knowledge/theory/models.py` | domain-specific review states including accepted and rejected |
| Architecture Review | `AI-Gateway/app/architecture/models/review_status.py` | open/final architecture review with approved or rejected outcomes |
| Repository evolution | `AI-Gateway/app/architecture/repository/evolution_models.py` | proposed, approved, rejected decisions within evolution plans |
| Repository recovery and closure | repository recovery and closure modules | separate recovery authorization and closed/blocked outcomes |
| Screening | `deploy/postgres/init/020_screening_decisions.sql` | eligible, ineligible, human_review_required |
| Restore verification | `deploy/postgres/init/029_backup_restore_contracts.sql` | verified, blocked, failed |

Repository fact: these states occur in different constructors, services,
tests, and persistence constraints.

Analytical finding, confidence **High**: identical words do not establish a
shared lifecycle. Bounded-context isolation is required.

### 6.2 Evidence-to-theory safety

Repository facts:

- extraction produces provisional evidence;
- `AI-Gateway/app/knowledge/modeling/admission.py` admits only accepted
  evidence with review provenance;
- graph models reject rejected or non-accepted evidence;
- theory builder rejects sources not accepted by human review;
- PostgreSQL evidence repository maps live review state and validates review
  provenance;
- tests cover provisional, rejected, accepted, mixed, and stale-review paths.

Analytical finding, confidence **High**: canonical graph and theory
construction contain defense-in-depth evidence-admission controls.

### 6.3 Persistence authority and immutability

Repository facts:

- `deploy/postgres/init/010_storage_contract_registry.sql` classifies
  PostgreSQL resources as canonical, immutable ledger, representation,
  derived, or operational staging;
- evidence review events, provenance events, artifact lifecycle events, AI
  review events, identity decisions, screening decisions, knowledge intake,
  and restore verification use immutable or append-only patterns;
- canonical graph nodes and edges are backed by canonical objects and review
  provenance;
- embedding index is explicitly derived and rebuildable;
- compatibility filesystem data is explicitly non-canonical when database and
  object storage are configured;
- multiple content-hash constraints require lowercase 64-character hashes.

Analytical finding, confidence **High**: the repository declares and enforces
multiple canonical and immutable persistence boundaries. This does not prove
the contents or health of a live database.

### 6.4 Tests and CI

Repository facts:

- 85 test files exist under the application tree at the exact revision;
- architecture tests cover schema compatibility, ARC generation and
  publication, transactional persistence, laws, compliance, review, API,
  repository health, traceability, evolution, and recovery;
- knowledge tests cover discovery, evidence, graph, theory, publication,
  validation, and product behavior;
- `.github/workflows/architecture-quality-gates.yml` declares jobs for full
  regression, knowledge/product regression, container/deployment contracts,
  PostgreSQL/MinIO integration, schema/ARC/persistence gates, and dependency
  security;
- the governance-contract job runs schema compatibility, ARC generator, ARC
  publisher, and transactional persistence tests.

Analytical finding, confidence **High** for declared coverage and **Limited**
for execution at the exact revision: workflow definitions and tests are
present; live Actions results are outside the snapshot boundary.

### 6.5 Deployment and recovery

Repository facts:

- 18 verifier artifacts cover canonical storage, artifacts, evidence, graph,
  publications, semantic index, source inspection, screening, monitoring,
  workers, representations, recovery coverage, and restore coordination;
- migrations 029--032 define backup/restore contracts, signed restore-evidence
  admission, restore coordination, and scheduling;
- restore evidence must match an eligible canonical backup and complete
  required component checks;
- repository evolution recovery and post-verification artifacts explicitly do
  not authorize production activation.

Analytical finding, confidence **High** for repository contracts and
**Limited** for operational state: recovery governance is implemented and
fail-closed in source, but no live restore execution is observed.

## 7. Existing Baseline-Labelled Artifacts

| Artifact | Local function | Observed status or effect | Why it is not reclassified |
| --- | --- | --- | --- |
| `Documents/FILE_MANAGEMENT_SAFETY_BASELINE.md` | completion and safety evidence for FMA-001 through FMA-008 at a named commit | completed and verified capability set; production mutation prohibited | it is a local implementation-acceptance baseline, not a cross-governance observational snapshot |
| `Documents/MAINTENANCE_BASELINE_AUDIT.md` | audit of 30 maintenance-charter rules and staged roadmap | initial evidence-based maintenance baseline | it combines implementation audit and roadmap input |
| `Documents/ONE_FILE_ONE_ARCHITECTURAL_RESPONSIBILITY.md` | OFAR evidence audit and staged governance baseline | report-only; no blocking law or automated refactoring | it is an engineering rule audit and Architecture review signal |

Repository fact: the word `baseline` predates the Governance Baseline working
specification and has local meanings.

Analytical finding, confidence **High**: shared terminology does not establish
shared artifact type, lifecycle, authority, or precedence. This snapshot does
not apply the Governance Baseline specification retroactively.

## 8. Root Repository Governance Evidence

| Artifact | Actual observed role | Authority effect | Limitation |
| --- | --- | --- | --- |
| `README.md` | project description, architecture orientation, start paths, and document index | informative project entry point | not a global governance authority |
| `CONTRIBUTING.md` | contribution expectations and safety checks | contributor process guidance | repository enforcement and exception authority are not fully defined |
| `SECURITY.md` | supported-version and vulnerability-reporting policy | security process guidance | does not prove live private-reporting settings |
| `SUPPORT.md` | best-effort support boundary and current target | operational expectation setting | no service-level guarantee |
| `CODE_OF_CONDUCT.md` | community behavior expectations | community policy | investigation and enforcement state are external |
| `CITATION.cff` | software citation metadata | publication metadata | does not govern scientific-evidence acceptance |
| `LICENSE` | Apache License 2.0 terms | legal license artifact | legal effect is outside this architecture review |
| `NOTICE` | attribution notice | legal/distribution metadata | not project governance authority |

Analytical finding, confidence **High**: these files provide real local
process, community, security, support, citation, and legal roles. Their
presence does not automatically form a unified global governance layer.

## 9. Governance Landscape

| Governance area | Observed state | Evidence basis | Confidence |
| --- | --- | --- | --- |
| Project direction | working direction | accepted vision, governing vision, strategic roadmap, maintenance charter | Moderate |
| Scientific governance | operational domain controls plus working framework vision | SGF, knowledge code, SQL, tests, verifiers | High for controls; Moderate for framework status |
| Architecture governance | operational software-governance subsystem | graph, laws, compliance, reviews, ARC, roles, persistence, tests | High |
| Architecture Law governance | audited but incomplete | Architecture Law Governance Audit | High for gap |
| Repository governance | operational observation and guarded evolution; activation restricted | FMA, repository code, tests, safety baseline | High |
| Engineering governance | working charter with partial/implemented audit evidence | Long-Term Engineering Charter and Maintenance Baseline Audit | Moderate |
| Documentation governance | local conventions only; no evidenced global governance | status headers, README index, contribution rules, working specifications | High for absence within scope |
| Roadmap governance | multiple accepted working roadmaps without global roadmap governance | Internet Discovery, Autonomous Intelligence, Scientific Knowledge roadmaps | Moderate |
| Deployment governance | operational contracts and verifiers; live state unobserved | compose, migrations, restore and deployment verifiers, CI | High for definitions; Limited for live state |
| Decision memory | distributed and domain-local | review events, provenance ledgers, PR URLs, architecture decisions, scientific review events | Moderate |
| Project Phase governance | not evidenced as a repository framework | phase terms occur, but no Project Phase Framework artifact exists | High for bounded absence |
| Governance evidence plane | emerging working architecture | two governance working specifications plus audits and immutable domain evidence | Moderate |

### 9.1 Operating governance

Analytical classification:

- scientific evidence admission;
- architecture validation, review, and ARC generation;
- repository observation and guarded evolution;
- canonical persistence and immutable decision ledgers;
- deployment, recovery, and CI contract definitions.

These are operating within their domain and implementation boundaries.

### 9.2 Working direction

Analytical classification:

- project vision and responsible evolution;
- scientific framework vision;
- file-management architecture;
- internet-discovery and autonomous-intelligence roadmaps;
- long-term engineering charter;
- governance status boundary and Governance Baseline specifications.

Their status claims are present, while formal ratification remains undefined.

### 9.3 Partial or absent governance

Analytical classification:

- Architecture Law authority is partial and audited;
- documentation governance is not evidenced globally;
- roadmap governance is not evidenced globally;
- decision memory is distributed;
- Project Phase governance is not present;
- cross-governance precedence is absent;
- baseline issuance and correction authority are absent.

## 10. Authority Evidence and Gaps

### 10.1 Authority and permission matrix

| Authority or permission | Repository evidence | What it supports | What it does not support |
| --- | --- | --- | --- |
| Project-owner evidence | status headers and decision records in visions, working architectures, roadmaps, charters, and specifications | bounded project direction and recorded working decisions | formal ratification, global precedence, or undocumented later decisions |
| Architecture runtime roles | `AI-Gateway/app/architecture/authentication.py` | scanner, law_admin, reviewer, approver, publisher, auditor API permissions | authority to ratify project governance or documentation |
| Architecture reviewer/approver | review engine, pipeline, API, models, tests | finding decisions and Architecture Review finalization | approval of unrelated governance instruments |
| Scientific reviewer | evidence and theory review models, repositories, SQL, tests | human evidence and theory decisions in the scientific domain | project governance authority |
| Repository permissions | repository decision, preflight, execution, recovery, and closure models | bounded evolution and recovery controls | automatic production activation or global file-law authority |
| PR and CI permissions | tracked workflows and external decision URLs | declared automated checks and traceable external references | live repository permissions, branch protection, or external decision content |
| Deployment/recovery controls | SQL contracts, restore controllers, verifiers, signing trust artifacts | fail-closed backup and isolated restore evidence | evidence that live deployment or restore is currently healthy |

### 10.2 Separated authority classes

- **Governance authority**: formal authority to create binding governance is
  not defined repository-wide.
- **Operational permission**: runtime roles and service checks authorize
  bounded API or operational actions.
- **Repository permission**: GitHub and local Git permissions are external to
  the tracked tree.
- **Review authority**: domain review engines accept named reviewers or roles
  within their bounded context.
- **Implementation authorization**: plans, decisions, and approvals are
  capability-specific; a document or baseline does not imply it.
- **Activation authorization**: repository evolution and recovery artifacts
  explicitly keep production activation false or separate.

Analytical finding, confidence **High**: the repository contains substantial
operational and review permission evidence but no formal repository-wide
governance-ratification or baseline-issuance authority.

## 11. Lifecycle and Terminology Boundaries

### 11.1 Evidenced lifecycle families

| Lifecycle or status family | Bounded context | Evidence |
| --- | --- | --- |
| scientific artifact | scientific storage/publication | migration 003 and artifact lifecycle services |
| evidence review | extraction and evidence admission | extraction models, PostgreSQL evidence repository, migrations 004 and 022 |
| theory review | theory construction/publication | theory models, builder, publication engine, tests |
| Architecture Review | architecture governance | review status, review engine, pipeline, ARC generator |
| architecture validation | graph/law/compliance | validation reports, compliance engine, tests |
| public-contract compatibility | architecture/schema | contract registry, schema compatibility tests |
| repository evolution | repository management | planning, decision, preflight, dry run, execution, recovery, closure |
| deployment and recovery | operations | backup/restore migrations, controllers, verifiers |
| governance-instrument claims | project governance | Governance Instrument Status and Decision Boundary Specification |

### 11.2 Terminology conflicts

| Term | Observed meanings |
| --- | --- |
| accepted | evidence decision, theory decision, project-owner working direction, roadmap or architecture claim |
| approved | Architecture Review final state, repository evolution decision, ordinary prose |
| ratified | scientific artifact lifecycle and unimplemented/formally undefined governance claims |
| active | scientific publication or runtime state; not proof of governance effect |
| verified | restore outcome, test result, audit evidence, completion claim |
| completed | backup/run/capability milestone or prose; not a global terminal status |
| closed | repository evolution closure or workflow state |
| published | scientific artifact or release representation; not governance ratification |
| archived | scientific artifact lifecycle or historical storage |
| baseline | local implementation/audit reference or the newly specified governance observational artifact |

Analytical finding, confidence **High**: terminology is locally meaningful and
cannot be normalized without changing domain contracts. This snapshot
preserves isolation and does not define a global lifecycle.

## 12. Dependency Map

### 12.1 Observed and declared dependencies

```text
Project direction artifacts
  -> supply working intent to roadmaps, charters, and domain governance

Scientific Governance Framework
  -> supplies framework vision
      -> scientific code, persistence, tests, and verifiers provide partial
         implementation evidence

Architecture Governance
  -> Architecture Graph
      -> law resolution and validators
          -> compliance report
              -> Architecture Review
                  -> ARC package and publication boundary

File Management Architecture
  -> architecture repository inventory and policy
      -> health and traceability
          -> guarded evolution and recovery

Internet Discovery Roadmap
  -> discovery contracts and source registry
      -> inspection and screening
          -> extraction and human review
              -> knowledge intake
                  -> graph and theory safety

Status and Decision Boundary Specification
  -> Governance Baseline Specification
      -> this separately constructed observational snapshot draft
```

### 12.2 Dependency classes

- **Declared dependency**: explicitly stated in a tracked document, such as
  the governance bootstrap chain.
- **Observed dependency**: directly represented by imports, constructors,
  persistence references, workflow steps, or document links.
- **Inferred analytical dependency**: derived from multiple evidence items,
  such as working project direction informing domain roadmaps.
- **Unresolved dependency**: named but not implemented or assigned, such as
  baseline issuance authority.
- **Unsupported claim**: a claimed dependency without admitted evidence; none
  is promoted to the map.

### 12.3 Circular-dependency review

Repository fact: the two working specifications explicitly prohibit
self-authorization and separate baseline, specification, authority decision,
implementation, and verification.

Potential circular paths:

- a baseline issuing itself;
- a specification using its own text as ratification authority;
- an Architecture Review `APPROVED` state being treated as approval of project
  governance;
- project-owner status text being treated as the formal authority definition
  that validates that same status;
- a future baseline being required to create the authority needed to issue
  the first baseline.

Analytical finding, confidence **High**: the draft construction path avoids
these cycles because it claims no issuance or approval. The issuance cycle
remains unresolved and would reappear if this draft were promoted without a
separate authority model.

This dependency map is descriptive and creates no precedence rule.

## 13. Conflicts, Ambiguities, Gaps, and Limitations

### 13.1 Required recorded findings

1. **Stage 0--2 durability gap** — the stages are referenced, but complete
   standalone reports are absent from the exact revision.
2. **Historical wording ambiguity** — working specifications retain instances
   of `this draft`; the status headers and durable decision sections show
   working direction, but the stale wording remains.
3. **Project-owner authority ambiguity** — multiple files claim project-owner
   authority while formal ratification authority is undefined.
4. **Baseline terminology conflict** — three earlier artifacts use
   `baseline` for local implementation or audit purposes.
5. **Cross-context status conflict** — shared terms have different scientific,
   architecture, repository, operational, and project-governance meanings.
6. **External decision limitation** — GitHub decision URLs are tracked, but
   their content is not reproducible offline.
7. **Live-state limitation** — PostgreSQL, MinIO, deployment, worker, browser,
   and runtime states are not observed.
8. **Issuance-authority gap** — no authority to issue a Governance Baseline is
   defined.
9. **Correction-authority gap** — correction traceability is specified, but
   correction-record authority and status are not.
10. **Material-change authority gap** — inputs are specified, but final
    criteria and decision authority are not.
11. **Registry and identifier gap** — no global governance registry,
    identifier family, or version convention exists.
12. **Documentation-governance gap** — repository-wide document
    classification, precedence, publication, change, and retirement governance
    is absent.
13. **Cross-governance precedence gap** — no global conflict-resolution or
    precedence rule exists.
14. **Project Phase governance gap** — no Project Phase Framework or canonical
    phase registry is present.
15. **CI execution limitation** — workflow definitions are present, but live
    execution results at the observation boundary are external.

### 13.2 Effect on this snapshot

The gaps reduce authority and external-state confidence, but they do not
prevent repository observation. None is resolved by assumption. They prohibit
claims of issuance, ratification, canonical status, global precedence,
operational health, or governance completion.

## 14. Confidence Assessment

| Main conclusion | Confidence | Basis | Limitation |
| --- | --- | --- | --- |
| Two project-governance working specifications exist | High | exact tracked files, headers, decision sections | external PR content not offline |
| Their formal ratification and enforcement are absent | High | explicit status and non-effect text | later external governance could exist outside scope |
| Project direction is recorded as accepted working direction | Moderate | multiple consistent document headers | formal authority framework absent |
| Scientific governance has operative controls | High | enums, constructors, SQL, repositories, tests, verifiers | live data excluded |
| Architecture governance is operational in software scope | High | source, roles, review engine, ARC, tests | active law-bundle authority remains unresolved |
| Repository governance has guarded evolution controls | High | FMA, implementation, tests, safety baseline | production activation external/prohibited |
| Deployment and recovery contracts exist | High | SQL, controllers, verifiers, workflows | live deployment and restore state excluded |
| Documentation governance is globally absent | High within scope | repository-wide search and explicit unresolved dependencies | external policy could exist outside repository |
| Decision memory is distributed | Moderate | domain ledgers, review models, PR references | no global registry and external PR content |
| Project Phase governance is absent | High within scope | no framework or registry artifact | informal phase usage exists |
| No baseline issuance authority exists | High within scope | explicit unresolved-dependency lists | an external authority model is not observed |
| This snapshot cannot be authoritative | High | specification non-effect and construction status | none within stated scope |

Confidence describes evidentiary support only. It does not approve or validate
governance.

## 15. Final Observational Finding

At repository revision
`c0957d233aa3da0a74b849c639b0506654c1f929`, ResearchOS contains:

- recorded project-owner working direction across vision, evolution,
  scientific, architecture, repository, roadmap, and engineering artifacts;
- operational scientific evidence, architecture governance, repository
  management, persistence, verification, deployment, and recovery controls
  within bounded contexts;
- two project-governance working specifications that separate status,
  observation, decision, implementation, and verification;
- immutable or content-addressed domain evidence and decision mechanisms;
- tests, CI definitions, SQL constraints, and deployment verifiers supporting
  many implementation claims; and
- explicit safety boundaries against machine ratification, evidence bypass,
  self-authorization, and implicit production activation.

The same revision does not provide repository evidence for:

- formal repository-wide governance or ratification authority;
- Governance Baseline issuance or correction authority;
- global documentation, roadmap, or Project Phase governance;
- cross-governance precedence;
- a global governance identifier, registry, publication, retention, or
  closure mechanism;
- complete standalone Stage 0--2 reports;
- fully offline external decision evidence; or
- live PostgreSQL, MinIO, deployment, recovery, worker, CI-result, and runtime
  state.

The observed dependency direction runs from project direction and local domain
governance through working governance specifications to this separately
constructed observational draft. Authority gaps remain unresolved. The
validity of this snapshot is limited to the named Git revision, included
paths, methods, exclusions, and limitations.

This conclusion is observational. It gives no recommendation, approval,
ratification, issuance, implementation authorization, activation decision,
canonical status, binding effect, or precedence.
