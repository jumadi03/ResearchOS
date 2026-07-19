# Canonical Discovery and Source Inspection Acceptance

Date: 2026-07-19  
Target UI: `http://localhost:3003/`  
Role: discoverer  
Migration stage: 3

## Decision

**ACCEPTED for local discovery through source screening.**

The canonical UI can create a governed literature-discovery run, display
provider provenance, enrich metadata, acquire an enumerated scientific
document, verify its checksum, inspect its structure, and screen it against the
bound discovery contract.

Evidence extraction was intentionally not exposed in this stage.

## Implemented workflow

1. Load provider and limit capabilities from the backend.
2. Bind a human-authored research question and query concept.
3. Construct a discovery contract with project, question, plan, provider,
   retrieval budget, year range, document type, evidence type, license policy,
   stopping condition, and human-review policy.
4. Submit the run with session CSRF.
5. Display deduplicated records without treating them as evidence.
6. Display provider, rank, source count, snapshot, and response SHA-256.
7. Enrich the selected run with metadata and citation observations.
8. Acquire only a URL matching enumerated source metadata.
9. Verify downloaded document integrity.
10. Run source inspection and contract screening.

## Browser acceptance

The exact DOI query `10.3389/fdata.2022.971974` was used.

- Discoverer authentication passed.
- OpenAlex capability loaded from the backend.
- The run returned one unique record and zero provider failures.
- The resolved article was
  `Sharing social media data: The role of past experiences, attitudes, norms,
  and perceived behavioral control`.
- Provider response hash and discovery snapshot were displayed.
- Metadata enrichment produced 1 observation and 68 citation edges.
- An official Frontiers URL using the current journal path was rejected because
  it did not exactly match the URL enumerated in the OpenAlex source metadata.
- The enumerated legacy Frontiers PDF URL was then accepted.
- Document checksum/integrity verification passed.
- Source inspection integrity passed.
- Contract screening returned `eligible`.
- The UI stopped at “ready for the next extraction gate”; no evidence objects
  were created by this acceptance.

The rejected acquisition attempt caused no document mutation.

## Trust boundaries

- Only a discoverer session receives the discovery surface.
- Provider choices and numeric limits come from backend capabilities.
- Result records remain discovery candidates.
- Source provider and response hash are locked from the selected record.
- URL matching is enforced by the backend and was not relaxed.
- Inspection and screening run before any future extraction.
- No `/extractions` request exists in the stage-3 UI implementation.

## Automated verification

- Production UI build: passed.
- Site tests: **7 passed, 0 failed**.
- Targeted discovery, acquisition, inspection, screening, and API regression:
  **68 passed, 0 failed**.

## Remaining boundary

Discovery runs and document gates are persisted by the backend, but there is
currently no canonical read endpoint for reopening a prior discovery run after
a browser refresh. Adding a run-history read model should precede full legacy
workspace retirement.

The next migration stage is governed evidence extraction, screening, and human
review from the accepted source.
