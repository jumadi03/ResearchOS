# Multi-Source Scientific Workflow Pilot

## Outcome

On 2026-07-16, ResearchOS completed a real two-source workflow using two
independent discovery providers. Both open-access publications progressed from
metadata discovery and PDF acquisition through evidence review, graph creation,
theory synthesis, validation, and an integrity-verified publication package.

The validation result remained `incomplete`. This is the correct outcome: the
three generated theories each drew support from only one independent graph, so
the replication threshold was not met.

## Sources

1. *Open science practices in general and internal medicine journals, an
   observational study* — PLOS ONE, 2022,
   [DOI 10.1371/journal.pone.0268993](https://doi.org/10.1371/journal.pone.0268993),
   discovered through OpenAlex.
2. *Reproducibility and replicability in research: What 452 professors think in
   Universities across the USA and India* — PLOS ONE, 2025,
   [DOI 10.1371/journal.pone.0319334](https://doi.org/10.1371/journal.pone.0319334),
   resolved through Crossref.

Both publisher pages identify their articles as open access under the Creative
Commons Attribution License. The pilot acquired publisher-hosted HTTPS PDFs and
did not bypass access controls.

## Verified results

| Stage | 2022 source | 2025 source |
| --- | ---: | ---: |
| Metadata observations | 1 | 1 |
| Citation edges | 20 | 39 |
| PDF bytes | 651,962 | 2,953,340 |
| Reviewed evidence objects | 7 | 7 |
| Graph nodes | 8 | 8 |
| Graph edges | 17 | 10 |

Combined workflow results:

| Stage | Result |
| --- | --- |
| Theory synthesis | 3 proposals |
| Human theory review | 3 proposals accepted by the reviewer principal |
| Gap analysis | 3 gaps |
| Validation | `incomplete` |
| Validation reason | Independent replication threshold not met |
| Literature-review publication | Package integrity verified |

Canonical pilot identifiers:

- discovery runs: `discovery-1d00011829754d6a9332cac98564ca57` and
  `discovery-98f31fa0e42343c6a4b29fce9b9eda77`;
- graphs: `graph-df1ab371878d07b8083c6357` and
  `graph-568761635dac3988c1d322f7`;
- theory bundle: `theory-bundle-972a927f615d888dda286ddf`;
- validation report: `validation-52f7826f2b849326dbecf581`; and
- publication: `publication-b003b5134ff31d5cce685ebd`.

These identifiers contain no credentials or private research data.

## Defects found and corrected

### Structured Crossref licenses

Crossref returns license metadata as a list of structured records. PostgreSQL
previously received that list for a text column. ResearchOS now selects the
provider's license URL, persists it as text, and marks access as open only when
an explicit provider signal or Creative Commons URL supports that conclusion.

### Exact DOI resolution

Crossref DOI input previously went through ranked bibliographic search, where a
valid target could fall outside the requested result limit. Exact DOI queries
now use Crossref's work endpoint; ordinary topical queries retain ranked search.

Both corrections have regression coverage.

## Interpretation

This pilot proves multi-provider ingestion and end-to-end provenance, not that
the publications independently replicate the same claim. The theory builder
kept study-specific assertions separate, leaving every theory with one
independent supporting graph. ResearchOS therefore refused to report a
validation pass while still producing an integrity-verified review artifact.

## Follow-up

- Define a reviewed cross-graph claim-consolidation method that can identify
  semantically equivalent assertions without erasing study-specific context.
- Add a pilot whose independent studies explicitly test the same scoped claim.
- Preserve the current fail-safe replication threshold and reviewer-visible
  validation reasons.
