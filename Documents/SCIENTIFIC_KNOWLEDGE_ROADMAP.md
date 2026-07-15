# Scientific Knowledge Subsystem

## Status

- Document status: accepted architecture baseline
- Roadmap: SK-001A through SK-001I
- Completed: SK-001A Literature Discovery
- Completed: SK-001B Metadata and Citation Collector
- Completed: SK-001C Document Acquisition and Registry
- Completed: SK-001D Evidence Extraction Engine
- Completed: SK-001E Scientific Knowledge Graph
- Completed: SK-001F Theory Builder
- Completed: SK-001G Research Gap Detection
- Completed: SK-001H Validation Engine
- Completed: SK-001I Publication Engine
- Roadmap status: SK-001A through SK-001I implemented

## Implementation status

SK-001A is implemented in `app/knowledge`. It includes:

- canonical question, search-plan, source-record, literature-record,
  provider-failure, and discovery-run contracts;
- OpenAlex, Crossref, and Semantic Scholar HTTP adapters;
- provider-specific normalization and canonical raw-response hashing;
- exact DOI deduplication that retains every source record;
- reviewable fuzzy-title match detection without destructive merging;
- explicit partial-failure results;
- byte-stable, content-addressed discovery snapshots;
- cursor/offset multi-page collection with provider result limits;
- bounded retry/backoff with `Retry-After` handling;
- provider response caching and immutable raw-page persistence;
- environment-based provider, output, and secret configuration; and
- a fail-closed authenticated discovery application/API service.

SK-001B is implemented in `app/knowledge/retrieval`. It
adds provenance-preserving metadata observations, citation edges, explicit
field conflicts, correction/retraction lifecycle signals, resolved enrichment
views, content-addressed schema-versioned snapshots, and an authenticated
metadata endpoint bound to a discovery run.

SK-001C is implemented in `app/knowledge/ingestion`. It adds explicit access
and license policy, provenance-bound acquisition candidates, HTTPS-only PDF
retrieval, media and signature validation, configurable size limits,
content-addressed immutable blobs, versioned document manifests, integrity
verification, and metadata-only registry entries when access rights are not
explicitly open.

SK-001D is implemented in `app/knowledge/extraction`. It extracts structured
scientific objects from integrity-verified PDFs, records page and character
coordinates plus quote hashes, identifies methods, results, conclusions, and
claim patterns, assigns explicit confidence, keeps all machine output in a
provisional review state, and persists content-addressed extraction manifests
with parser and schema versions.

SK-001E is implemented in `app/knowledge/modeling`. It builds deterministic,
versioned graphs containing source-document and scientific-object nodes plus
typed `CONTAINS`, `USES_METHOD`, and `SUPPORTS` edges. Every relationship is an
explicit assertion carrying extraction, document, object, page, quote-hash,
confidence, and review-state provenance. Graph snapshots are content-addressed
and integrity verified before persistence.

SK-001F is implemented in `app/knowledge/theory`. It synthesizes traceable
theory proposals across verified knowledge graphs, aggregates supporting and
contradicting evidence stances, represents competing proposals with explicit
rationale, and persists integrity-verified bundle snapshots. Machine-generated
proposals remain `PROPOSED`; acceptance or rejection requires an attributable
human review event with rationale and produces a new immutable snapshot.

SK-001G is implemented in `app/knowledge/gaps`. It applies a versioned,
deterministic taxonomy for evidence absence, limited coverage, and unresolved
contradiction; records the triggering rule, severity, theory IDs, and evidence
edge IDs; and produces evidence-linked advisory hypothesis proposals. Gap
analyses are content-addressed and integrity verified before persistence.

SK-001H is implemented in `app/knowledge/validation`. It applies a transparent
versioned assessment method to traceable support, independent graph count,
contradictions, reviewer-supplied risk-of-bias state, and search age. Reports
record every input, factor, reason, evidence edge, and reviewer identity.
Fail-safe statuses are `PASS`, `FAIL`, `INCOMPLETE`, and `STALE`; missing
evidence or an unknown bias assessment can never produce `PASS`.

SK-001I is implemented in `app/knowledge/publication`. It renders canonical
evidence-linked Markdown for literature reviews, scoping reviews, systematic
review support, and research proposals. Citation verification and validation
status are release gates; systematic-review support requires `PASS`.
Publication manifests record input identities and hashes, engine version,
generator identity, Markdown checksum, and citation verification. Released
packages are immutable and reproducible from their verified inputs.

## Vision

ResearchOS starts from a phenomenon or scientific question, not from a paper.
The Scientific Knowledge Subsystem turns discoverable literature into
traceable, structured, and reviewable scientific knowledge.

The governing progression is:

```text
Reality -> Phenomenon -> Scientific Object -> Scientific Construct
        -> Scientific Theory -> Operational Model -> Measurement -> Application
```

For literature-assisted research, the operational pipeline is:

```text
Phenomenon or Scientific Question
    -> Literature Discovery
    -> Metadata Retrieval
    -> Document Acquisition
    -> Evidence Extraction
    -> Knowledge Modeling
    -> Theory Construction
    -> Measurement
    -> Validation
    -> Publication
```

Papers are sources. They are not, by themselves, canonical scientific
evidence or knowledge.

## Architectural position

The subsystem is a Level-6 component. A Level-7 Scientific Knowledge Engine
coordinates Level-8 capabilities. The engine owns orchestration and workflow
state; each capability owns one bounded operation and its contracts.

```text
ResearchOS
└── Kernel (Level 5)
    └── Scientific Knowledge Subsystem (Level 6)
        └── Scientific Knowledge Engine (Level 7)
            ├── Literature Discovery (Level 8)
            ├── Metadata Retrieval (Level 8)
            ├── Document Acquisition (Level 8)
            ├── Evidence Extraction (Level 8)
            ├── Citation Analysis (Level 8)
            ├── Knowledge Graph (Level 8)
            ├── Theory Builder (Level 8)
            ├── Research Gap Detection (Level 8)
            ├── Hypothesis Generation (Level 8)
            ├── Validation (Level 8)
            └── Publication (Level 8)
```

The target package layout is evolutionary. Directories are introduced only
when their sprint begins.

```text
app/knowledge/
    discovery/
    retrieval/
    ingestion/
    extraction/
    modeling/
    validation/
    publication/
```

## Bounded contexts and canonical terms

The following distinctions are mandatory:

- `LiteratureRecord` is normalized bibliographic metadata returned by a
  literature source. It may describe an article, preprint, dataset, review, or
  other scholarly work.
- `SourceDocument` is an acquired, content-addressed representation of a
  scholarly work. Acquisition metadata must include its rights and access
  status.
- `ScientificEvidence` retains its current Discovery-domain meaning: evidence
  extracted from a scientific observation record. It must not be reused as
  the name for paper metadata.
- `ScientificClaim`, `ScientificMethod`, `ScientificDataset`, and
  `ScientificResult` are extraction outputs with provenance back to a source
  document and location.
- `KnowledgeGraph` relates sources, claims, methods, variables, datasets,
  results, constructs, and theories. Graph edges are assertions with
  provenance, not unqualified facts.
- `TheoryAssessment` records measured support, contradiction, replication,
  bias, and uncertainty. A score without its method and inputs is invalid.
- `PublicationArtifact` is a derived output. It never becomes evidence merely
  because ResearchOS generated it.

This vocabulary prevents the discovery result, the source document, and the
scientific evidence extracted from that document from collapsing into one
object.

## Trust and provenance rules

1. Every record must retain source, retrieval time, source identifier, and raw
   source reference or response hash.
2. Deduplication must be reversible. Merged records retain all source-specific
   identifiers and values.
3. DOI is a useful identifier, not a universal primary key. Internal stable
   identifiers are required for works without a DOI and for versioned works.
4. Extracted claims and results must point to document locations. Unsupported
   AI output is advisory and cannot be promoted to validated knowledge.
5. Provider ranking, query expansion, extraction prompts, model versions, and
   scoring methods must be recorded for reproducibility.
6. Missing, inaccessible, retracted, or conflicting material remains visible
   as state; it must not be silently discarded.
7. Document acquisition must respect licenses, access controls, robots rules,
   and provider terms. Metadata availability does not imply a right to store a
   full document.
8. Human review decisions and machine assessments are separate, attributable
   events.

## Capability flow

### 1. Literature discovery

Accepts a phenomenon or scientific question and a reproducible search plan.
Adapters query supported providers and return source-native records. A
normalizer produces `LiteratureRecord` instances; a deduplicator groups likely
representations of the same work without deleting source records.

Initial providers are OpenAlex, Crossref, and Semantic Scholar. Provider
failure is represented explicitly and does not invalidate successful results
from other providers.

### 2. Metadata retrieval and citation collection

Enriches records with identifiers, abstracts, concepts, references, citation
links, publication type, venue, authorship, open-access state, and retraction
or correction signals when available. Conflicting provider values are retained
with provenance.

### 3. Document acquisition and registry

Resolves lawful document locations, records access outcomes, verifies content
type, calculates content hashes, and registers document versions. The registry
must support metadata-only records and must never treat acquisition failure as
absence of scientific evidence.

### 4. Evidence extraction

Parses a source into claims, methods, variables, datasets, results, and
conclusions. Each extraction carries document coordinates, extraction method,
model or parser version, confidence, and review state. This is scientific
parsing, not generic summarization.

### 5. Knowledge modeling

Builds a provenance-aware graph from reviewed or explicitly provisional
extractions. It represents support, contradiction, use, derivation,
replication, and citation as distinct edge types.

### 6. Theory construction and gap detection

Groups convergent and conflicting claims, maps constructs and relationships,
and proposes theories, gaps, and hypotheses. Proposed constructs and theories
remain advisory until reviewed under explicit validation policy.

### 7. Measurement and validation

Computes transparent assessments from declared inputs such as study design,
sample size, replication, risk of bias, directness, citation context, and
contradiction. `Theory Confidence Score` is not a universal truth value; it is
a versioned result of a named assessment method.

Validation answers scoped questions: whether evidence is sufficient for a
claim, whether contradictions are unresolved, whether the search is stale,
and whether an output satisfies its declared review protocol.

### 8. Publication

Produces traceable literature reviews, systematic or scoping review support,
meta-analysis inputs, proposals, and draft manuscripts. Every substantive
statement must be traceable to graph assertions and source locations. The
publication layer may format knowledge but may not invent validation status.

## Evolutionary roadmap

### SK-001A — Literature Discovery

Deliverables:

- canonical `ScientificQuestion`, `SearchPlan`, `LiteratureRecord`,
  `SourceRecord`, `DiscoveryRun`, and `ProviderFailure` contracts;
- provider interface plus OpenAlex, Crossref, and Semantic Scholar adapters;
- deterministic normalization and provenance-preserving deduplication;
- pagination, rate-limit, retry, timeout, and partial-failure behavior;
- persisted raw-response hashes and normalized discovery snapshots;
- contract, adapter, deduplication, and reproducibility tests.

Exit criteria:

- the same recorded provider responses produce byte-stable normalized output;
- every normalized field is traceable to one or more source records;
- one provider failure does not erase other provider results;
- exact identifier matches and uncertain fuzzy matches are distinguishable;
- no PDF download or evidence extraction is hidden in this capability.

### SK-001B — Metadata and Citation Collector

Deliverables include metadata enrichment, citation-edge collection, correction
and retraction signals, conflict representation, and snapshot versioning.

### SK-001C — Document Acquisition and Registry

Deliverables include lawful location resolution, access-state modeling,
content-addressed storage, document versioning, integrity checks, and a
metadata-only path.

### SK-001D — Evidence Extraction Engine

Deliverables include canonical extraction contracts, document coordinates,
structured parsing, confidence and review states, and a reproducible extraction
manifest.

### SK-001E — Scientific Knowledge Graph

Deliverables include a versioned graph schema, provenance-bearing assertions,
typed relationships, graph snapshots, and integrity validation.

### SK-001F — Theory Builder

Deliverables include construct and relationship synthesis, competing-theory
representation, support and contradiction aggregation, and review workflow.

### SK-001G — Research Gap Detection

Deliverables include explicit gap taxonomies, coverage and contradiction
analysis, hypothesis proposals, and evidence-linked explanations.

### SK-001H — Validation Engine

Deliverables include versioned assessment methods, bias and replication
signals, staleness checks, validation reports, and fail-safe status semantics.

### SK-001I — Publication Engine

Deliverables include protocol-aware review outputs, evidence-linked drafting,
export manifests, citation verification, and publication reproducibility
checks.

## SK-001A non-goals

The first sprint does not acquire PDFs, extract claims, construct a knowledge
graph, calculate evidence strength, generate hypotheses, or write a literature
review. It establishes trustworthy discovery inputs for those later stages.

Google Scholar is not an initial adapter. It may be evaluated later only when
there is a compliant, stable metadata access method. PubMed, arXiv, DOAJ, and
CORE are later adapter candidates after the provider contract is proven.

## Architecture decisions required before SK-001A implementation

1. Choose persistence for immutable raw provider snapshots and normalized
   discovery runs.
2. Define the stable identifier and work-version policy.
3. Define provider credentials, quotas, caching, and secret handling.
4. Approve the minimum `ScientificQuestion` and `SearchPlan` schemas.
5. Define the deduplication policy and threshold for human review.
6. Define data retention and deletion rules for provider responses.

## Success measures

- discovery coverage is measurable by provider and query;
- every result and merge decision is explainable;
- repeated processing of a snapshot is reproducible;
- downstream extraction never needs to infer where a record came from;
- theory and publication outputs can ultimately trace assertions to source
  locations through an unbroken provenance chain.
