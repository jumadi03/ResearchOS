# SGF-030 — Canonical Scientific Ontology

## Status

- Identifier: SGF-030
- Version: 1.0
- Document status: project-owner-directed operational standard
- Formal ratification status: not defined by current repository governance
- Classification: scientific ontology standard
- Owner: ResearchOS project
- Recorded: 2026-07-19
- Scope: canonical meaning and relations of ResearchOS scientific objects
- Depends on: SGF-000 and SGF-020
- Constrains: SGF-040, APIs, storage, graph, AI prompts and outputs, UI labels,
  validation, publication, and future SGF standards

This ontology defines semantic distinctions. It does not require every concept
to have a dedicated table or Python type today. Section 12 maps concepts to
existing implementation and identifies required extensions.

## 1. Purpose

SGF-030 prevents backend, AI, workspace, graph, and documentation from using
the same word with incompatible meanings. It establishes a minimum shared
language across disciplines while allowing domain profiles to add narrower
terms.

## 2. Ontology invariants

1. A source representation is not evidence until a traceable statement or
   object is extracted from it.
2. Extracted evidence is provisional until human review accepts it.
3. Accepted evidence is not automatically a fact.
4. A claim is not an observation merely because it appears in a source.
5. Interpretation and inference must not be presented as direct observation.
6. A hypothesis is testable and provisional; a theory is a structured
   explanatory synthesis with evidence and review history.
7. A confidence value is an assessment output, not probability of truth unless
   its method explicitly justifies that interpretation.
8. A graph edge remains an assertion with provenance.
9. Publication is a released representation, not epistemic promotion.
10. Translation, summary, and AI analysis are representations or advisory
    artifacts, not replacements for source content.

## 3. Foundational entities

### 3.1 Scientific Project

A bounded organizational context containing questions, workflows, actors,
objects, policies, and outputs. Project membership does not change the global
identity of content-addressed representations.

### 3.2 Research Question

An explicit question that defines what is being investigated. It may reference
a phenomenon and bounds discovery, evidence requirements, and validation.

### 3.3 Phenomenon

An occurrence, process, or pattern in the world selected for investigation.
The phenomenon is the subject of observation; it is not itself a statement
about what is true.

### 3.4 Construct

A defined conceptual entity used to organize or explain phenomena. A construct
must preserve its definition, scope, version, and operationalization.

### 3.5 Variable

A property capable of taking values within a defined domain. A variable is
distinct from a measurement, which is a recorded value produced by a method.

### 3.6 Population

The entities, cases, environments, or units to which an observation, claim, or
inference refers.

## 4. Source and representation entities

### 4.1 Scientific Source

A provider-specific observation of bibliographic or scientific material. It
preserves provider, external identity, retrieval time, response hash, access,
and license information.

### 4.2 Scientific Document

A canonical intellectual work resolved from one or more source observations.
Metadata conflict and version history must remain visible.

### 4.3 Representation

A concrete encoding of an object, such as PDF, HTML, XML, JSON, dataset,
Markdown, or supplementary file. It has media type, checksum, size, version,
storage location, and retrieval provenance.

### 4.4 Source Passage

An exact location within a representation, identified by coordinates and
content hashes. It is the traceability anchor for extracted evidence.

## 5. Epistemic entities

### 5.1 Observation

A recorded perception or detection produced under stated conditions. An
observation records what was observed, by whom or what, when, where, and by
which method. In current extraction contracts, an `observation` may still be a
source-author statement and therefore remains provisional evidence.

### 5.2 Measurement

An observation containing a value, unit or scale, measurement method,
conditions, and uncertainty where applicable.

### 5.3 Result

An output of an analysis or method applied to data. A result may summarize
measurements but must preserve the method and input provenance.

### 5.4 Claim

A declarative statement asserted by an identified actor or source. Claims may
be supported, contradicted, unresolved, or out of scope. A claim is never
treated as fact solely because it was published.

### 5.5 Evidence

A provenance-bound scientific object admitted for evaluating a claim,
hypothesis, model, or theory. Evidence must identify:

- source document and representation;
- exact source passage;
- extraction method and version;
- epistemic classification;
- review state; and
- applicable quality assessment.

`provisional evidence` is extracted material awaiting review. `accepted
evidence` has passed a human admission decision. `rejected evidence` remains
historical but is excluded from canonical knowledge admission.

### 5.6 Interpretation

A meaning assigned to observations, measurements, results, or claims by an
identified actor. It must not be rendered as directly observed content.

### 5.7 Inference

A conclusion derived from premises using an identified reasoning method. It
must preserve premises, method, assumptions, uncertainty, and limits.

### 5.8 Fact

A claim treated as established within an explicit scope after satisfying a
defined fact-admission policy. ResearchOS currently has no canonical,
general-purpose `Fact` admission contract. The existing
`observed_fact` epistemic classification describes reviewer interpretation of
a source statement; it must not be displayed as an unconditional canonical
fact.

### 5.9 Hypothesis

A testable provisional proposition derived from questions, evidence gaps,
observations, or inference. A hypothesis is advisory until reviewed and never
becomes a theory merely by accumulating generated text.

### 5.10 Model

A formal, computational, conceptual, statistical, or physical representation
used to describe, predict, simulate, or explain. It must identify assumptions,
parameters, domain of validity, method, and version.

### 5.11 Theory

A structured explanatory synthesis comprising a statement, accepted evidence,
supporting and contradicting relations, assumptions, scope, review state, and
validation history. Theory acceptance means admission as an accepted
ResearchOS theory object; it does not mean universal scientific truth.

## 6. Method and limitation entities

### 6.1 Method

A reproducible procedure with identity, version, inputs, parameters, outputs,
and applicability conditions.

### 6.2 Dataset

A versioned collection of recorded data with schema, provenance, access,
license, and integrity metadata.

### 6.3 Limitation

A bounded condition that reduces applicability, completeness, certainty, or
generalizability. Limitations attach to methods, evidence, models, theories, or
publications and must remain visible downstream.

### 6.4 Risk of Bias

A structured human assessment of systematic distortion risk. Current canonical
values are `low`, `some_concerns`, `high`, and `unknown`.

## 7. Governance and output entities

### 7.1 Decision

An authority-bearing event satisfying SGF-020. A decision is distinct from an
automated determination and an advisory proposal.

### 7.2 Validation Report

A versioned assessment produced by an explicit method from theory, evidence,
replication, contradiction, freshness, and risk-of-bias inputs. Current
statuses are `pass`, `fail`, `incomplete`, and `stale`.

### 7.3 Research Artifact

A governed output that moves through the canonical artifact lifecycle. It may
contain a report, synthesis, dataset, model, or publication package.

### 7.4 Publication

An immutable released representation of an eligible research artifact,
including a manifest, content hash, citations, validation reference, generator,
and release actor. Publication does not make its contents true.

### 7.5 Provenance Event

An immutable record linking an input, output, actor or agent, method,
configuration, and time.

## 8. Canonical relations

The shared relation vocabulary is:

| Relation | Meaning |
|---|---|
| `derived_from` | Target was produced using the source |
| `contains` / `part_of` | Structural containment without epistemic endorsement |
| `cites` | Refers to a source or object |
| `supports` | Provides evidence in favor of a claim or theory |
| `contradicts` | Provides evidence in tension with a claim or theory |
| `extends` | Adds scope or structure while retaining an explicit dependency |
| `replicates` | Attempts or achieves repetition under specified conditions |
| `uses_method` | Was produced using a method |
| `measures` | Measurement operationalizes or records a variable/construct |
| `has_limitation` | Associates an explicit limitation |
| `interprets` | Assigns meaning to another object |
| `infers_from` | Derives a conclusion through a named reasoning method |
| `supersedes` | Replaces current use while preserving history |
| `corrects` | Records a factual correction |
| `invalidates` | Makes an object or decision inadmissible under stated grounds |
| `represents` | Encodes another object in a concrete form |

Every epistemic relation must be an assertion with provenance and review state
where applicable. Relation labels must not bypass evidence admission.

## 9. Epistemic ladder and prohibited promotions

```text
Source
  -> Representation
    -> Source Passage
      -> Provisional Evidence
        -> Accepted Evidence
          -> Assertional Knowledge Graph
            -> Theory Proposal
              -> Accepted Theory
                -> Validation Report
                  -> Publication
```

This is an admission dependency, not a scale of truth. The following
promotions are prohibited:

- source -> fact;
- AI output -> accepted evidence;
- extraction confidence -> acceptance;
- accepted evidence -> fact;
- graph edge -> verified relationship;
- theory acceptance -> validation pass;
- validation pass -> universal truth;
- publication -> ratification of every claim.

## 10. Epistemic classification

Current extraction review uses:

- `observed_fact`;
- `source_author_interpretation`;
- `mixed`; and
- `unclear`.

For compatibility, these values remain valid. Their canonical interpretation
is:

- `observed_fact`: the reviewer judges that the extracted statement reports an
  observation or result as presented by the source; it is not canonical Fact;
- `source_author_interpretation`: meaning or conclusion attributed to the
  source author;
- `mixed`: inseparable observed and interpretive content;
- `unclear`: insufficient clarity for evidence acceptance.

A future migration should consider renaming `observed_fact` to
`source_reported_observation` while preserving schema compatibility.

## 11. Domain extension rules

A domain profile may add subtypes, relations, quality dimensions, and
lifecycle requirements when it:

- does not redefine a canonical term incompatibly;
- states the parent canonical concept;
- carries a version and owner;
- preserves provenance and human authority;
- defines validation and migration rules; and
- does not weaken SGF-020 or SGF-040.

## 12. Implementation traceability

### 12.1 Existing concepts

- `ScientificQuestionRequest` and discovery contracts;
- canonical scientific sources, documents, and representations;
- extracted object types `claim`, `method`, `variable`, `dataset`, `result`,
  `limitation`, `conclusion`, `population`, `observation`, and `measurement`;
- evidence coordinates, quote hashes, review states, and epistemic
  classification;
- assertional knowledge nodes and edges;
- theory proposal, evidence stance, competing theory, and review;
- risk of bias and validation report;
- research artifact and immutable publication representation;
- append-only provenance and decision events.

### 12.2 Compatibility gaps

- `pending` and `provisional` represent the same pre-review phase in different
  persistence boundaries;
- canonical `Fact`, `Interpretation`, `Inference`, `Hypothesis`, `Construct`,
  and general-purpose `Model` contracts are not fully implemented;
- relation review state is present in storage but not uniformly represented in
  every graph contract.

These gaps must be resolved through versioned migrations and compatibility
tests, not by changing UI labels alone.

### 12.3 SGF-030A implementation record

SGF-030A establishes one tested vocabulary across structured extraction,
PostgreSQL evidence persistence, and Knowledge Graph node types:

- `ScientificObjectType` defines the canonical extraction vocabulary;
- `CANONICAL_EVIDENCE_TYPES` exposes that vocabulary as a shared contract;
- `PERSISTENCE_EVIDENCE_TYPES` adds only the legacy generic `evidence` value
  required for backward compatibility;
- migration `021_extraction_manifests.sql` already admits `population`,
  `observation`, and `measurement`, so no redundant schema migration or schema
  version change was introduced;
- `KnowledgeNodeType` now preserves every canonical extraction type without
  semantic reduction; and
- `test_sgf_scientific_ontology.py` verifies exact vocabulary parity, legacy
  isolation, migration compatibility, and graph preservation.

This increment closes extraction-to-persistence-to-node-type alignment only.
It does not expand the graph relationship vocabulary or implement the missing
first-class concepts listed in Section 12.2.

### 12.4 SGF-030B explicit relation implementation

SGF-030B aligns the graph edge contract with the complete canonical relation
vocabulary in Section 8. The graph-construction contract can represent an
explicit relation assertion containing source evidence object ID, target
evidence object ID, relation type, and provenance evidence object ID.

The graph builder admits such an assertion only when all three referenced
objects belong to the selected extraction and have accepted review
provenance. Self-relations and references to unadmitted evidence fail closed.
The builder does not infer `measures`, `has_limitation`, `derived_from`, or any
other epistemic relation merely because two objects occur in the same
document. Explicit relations alter graph identity and remain assertional,
provenance-bound graph edges.

This increment establishes the operational substrate for structured
population, construct, outcome, direction, and limitation alignment. A
discoverer may propose only scientific relation types; a distinct reviewer
must accept the proposal; and an indexer may then reference its immutable ID
during intake. Structural and lifecycle relations such as `contains`,
`corrects`, and `supersedes` are not admitted through this path.

The increment does not declare two differently worded claims semantically
equivalent and does not remove the requirement for reviewer-governed theory
alignment.

### 12.5 Structured semantic re-extraction

The operational extraction path can now derive review candidates of type
`population`, `variable`, `measurement`, and `limitation` from exact passages
of accepted parent evidence. The deterministic
`researchos-semantic-annotation-parser` version `1.0.0` preserves the parent
document, screening, page, section, paragraph, page-text hash, character
range, and verbatim quote provenance.

These derived objects are lexical annotation candidates, not scientific facts
or accepted graph nodes. Every object is persisted as `provisional` in the
manifest and `pending` in PostgreSQL. Only accepted parent evidence may be
used as a source, an empty result fails closed, identical retries return the
same manifest, and no candidate is admitted to a graph before independent
human evidence review.

## 13. Verification plan

Ontology tests must verify:

- every stored type maps to one canonical concept;
- source, representation, evidence, and publication remain distinct;
- epistemic classification is not displayed as fact status;
- unsupported object or relation types fail closed;
- AI outputs retain advisory classification;
- graph edges preserve assertion and provenance semantics;
- domain extensions cannot redefine canonical terms; and
- schema/API/UI vocabulary remains consistent.

## 14. Definition of Done

SGF-030 is complete as an operational ontology when:

1. foundational, source, epistemic, method, governance, and output entities are
   defined;
2. Fact is explicitly bounded and not falsely claimed as implemented;
3. relations and prohibited promotions are explicit;
4. current epistemic classifications have safe meanings;
5. extension rules preserve the canonical vocabulary;
6. implementation mappings and incompatibilities are recorded; and
7. SGF-040 can assign lifecycle rules without redefining these concepts.
