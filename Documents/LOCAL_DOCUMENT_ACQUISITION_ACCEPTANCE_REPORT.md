# ResearchOS Local Document Acquisition Acceptance

Date: 2026-07-19  
Target: `http://127.0.0.1:8080/workspace`  
Status: **ACCEPTED — acquisition, extraction, governed review, and refresh persistence pass**

## Accepted path

- Browser control and the local Node kernel were operational.
- The workspace loaded 18 JavaScript/CSS assets with one automatic
  content-hash revision and `no-store` response headers.
- Exact DOI discovery for `10.3389/fdata.2022.971974` resolved the canonical
  OpenAlex record instead of an unrelated ranked-search result.
- Metadata enrichment completed before acquisition.
- The OpenAlex-enumerated PDF URL and `cc-by` license passed provenance
  binding, HTTPS retrieval, PDF validation, and checksum verification.
- Inspection was technically valid, article-type aliases passed the governed
  `journal_article` scope, screening was `eligible`, and extraction produced
  five evidence objects.
- PostgreSQL contains one canonical DOI document, one S3 representation, and
  five evidence objects. The representation points to
  `s3://researchos-documents/representations/81/81fd706a75ed80bda68c15b29af06a11c30d5d4e0c3b0df151b593193b389b5a.pdf`.

## Defects found and fixed

1. Workspace assets could retain a pre-policy browser cache entry. The
   workspace now emits automatic content-hash query revisions and clears the
   legacy cache on entry.
2. OpenAlex treated an exact DOI as ranked bibliographic search. Exact DOI
   input now uses the canonical OpenAlex work endpoint.
3. The browser attempted extraction without inspection and screening. The
   action now performs both governed gates before extraction.
4. A changed screening result reused an immutable decision identity and caused
   HTTP 500. Evaluated reasons now participate in the decision identity.
5. Provider values `article`, `journal-article`, and `JournalArticle` did not
   match the canonical contract value `journal_article`. Screening now
   normalizes these aliases.

## Reviewer acceptance

- Reviewer authentication and queue authorization passed.
- Normal evidence review now uses the complete governed assessment form:
  citation fidelity, context preservation, relevance, confidence assessment,
  epistemic classification, rationale, and explicit confirmation.
- Reviewed-statement and extraction-manifest hashes are bound from the
  canonical work queue and are not entered manually.
- A conservative rejection of the truncated claim was recorded with
  classification `unclear` and confidence `0.95`.
- The pending queue decreased from six to five. After a full browser refresh,
  it remained five and the rejected claim did not return.
- PostgreSQL confirmed the latest immutable event as `rejected`, attributed to
  `reviewer`, with both 64-character provenance hashes present. The evidence
  projection is also `rejected`.

## Regression evidence

- Targeted cache/API suite: 40 passed.
- Targeted discovery/cache/API suite: 61 passed.
- Targeted screening/discovery/API suite after final fixes: 65 passed.
- Full AI-Gateway regression suite: 502 passed.
