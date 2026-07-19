# ResearchOS Local Document Acquisition Acceptance

Date: 2026-07-19  
Target: `http://127.0.0.1:8080/workspace`  
Status: **PARTIALLY ACCEPTED — acquisition and extraction pass; reviewer submission remains blocked**

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

## Remaining blocker

Reviewer login and queue authorization work, and the five new evidence objects
appear in the local review inbox. Submitting a conservative rejection from the
canonical UI returns seven `Field required` validation errors because
`workspace.js` sends only `decision`, `rationale`, and `occurred_at`, while the
current API also requires citation fidelity, context preservation, relevance,
confidence assessment, epistemic classification, reviewed statement hash, and
extraction manifest hash.

Do not mark the end-to-end document-to-review workflow accepted until the
review dialog collects and submits those governed assessment fields (with the
two hashes sourced from canonical queue data) and a browser decision persists
after refresh.

## Regression evidence

- Targeted cache/API suite: 40 passed.
- Targeted discovery/cache/API suite: 61 passed.
- Targeted screening/discovery/API suite after final fixes: 65 passed.
- Full AI-Gateway regression suite: 502 passed.
