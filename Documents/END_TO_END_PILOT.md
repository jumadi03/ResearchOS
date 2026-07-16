# End-to-End Scientific Workflow Pilot

## Outcome

On 2026-07-16, ResearchOS completed a real local workflow from public literature
discovery through an integrity-verified publication package. The pilot used one
open-access article and deliberately retained an `incomplete` validation status
instead of overstating what a single source can establish.

## Source

- Article: *Open science practices in general and internal medicine journals,
  an observational study*
- DOI: [10.1371/journal.pone.0268993](https://doi.org/10.1371/journal.pone.0268993)
- Publisher: PLOS ONE
- License: Creative Commons Attribution (`CC-BY-4.0`)
- Acquisition: publisher-hosted HTTPS PDF

The publisher identifies the article as open access under the Creative Commons
Attribution License. The pilot recorded the license and provider provenance
before acquisition; it did not bypass access controls.

## Verified stages

| Stage | Result |
| --- | --- |
| API health | Passed |
| OpenAlex discovery | 1 record, 0 provider failures |
| Metadata collection | 1 provider observation and 20 citation edges |
| PDF acquisition | 651,962 bytes; checksum and object read-back verified |
| Deterministic extraction | 7 traceable provisional objects |
| Human evidence review | 7 objects accepted by the reviewer principal |
| Knowledge graph | 8 nodes, 17 assertion edges; integrity verified |
| Theory synthesis | 2 proposals |
| Human theory review | 2 proposals accepted by the reviewer principal |
| Gap analysis | 1 limited-coverage gap |
| Validation | `incomplete` |
| Literature-review publication | Package integrity verified |

Canonical pilot identifiers:

- discovery run: `discovery-9feaf2ffb0ee4fd89c75e73ec50df7d7`;
- document: `document-a3a2b5e67b77fa49e21c7ce6`;
- extraction: `extraction-b29cceaa997f5be06cf3fb89`;
- graph: `graph-df1ab371878d07b8083c6357`;
- theory bundle: `theory-bundle-10a00ddd5c8e8b20fc075d78`;
- validation report: `validation-23a2bfd837695300e37f8bc5`; and
- publication: `publication-ff415c876c5b6d0d41864c33`.

These identifiers contain no credentials or private research data.

## Defects found and corrected

### JSON-normalized artifact metadata

PostgreSQL returns JSON arrays while the in-memory theory metadata can contain
Python tuples. The artifact repository previously compared those container
types directly and reported a false integrity conflict even though canonical
JSON and the stored SHA-256 hash matched. Artifact retry verification now
compares canonical JSON values and retains the hash check. Regression coverage
includes nested theory metadata and a real-content mismatch.

### Reviewer authorization

Theory review, theory validation, and knowledge publication previously inherited
the default `discoverer` requirement. They now explicitly require the
`reviewer` role. Regression coverage confirms that a discoverer is rejected and
that reviewer attribution is preserved through validation and publication.

## Interpretation

The pilot demonstrates operational traceability, not scientific truth. Seven
accepted passages from one paper are still one-source evidence. ResearchOS
therefore recorded a limited-coverage gap and an `incomplete` validation result.
The publication package is reproducible and integrity-verified, but its content
remains a literature-review artifact requiring qualified human interpretation.

## Follow-up

- Explain allowed risk-of-bias values (`low`, `some_concerns`, `high`, and
  `unknown`) in user-facing validation documentation.
- Keep metadata observation, citation-edge, and conflict counts visible in the
  API and browser workspace so successful enrichment cannot be misread as empty.
- Repeat the pilot with multiple independent studies before evaluating a
  validation `pass` scenario.
