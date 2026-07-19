# Local Canonical Graph Explorer Acceptance Report

Date: 2026-07-20  
Environment: `http://localhost:3003/` and local ResearchOS API  
Result: Accepted locally

## Design outcome

The canonical UI now includes an Obsidian-inspired knowledge atlas:

- dark pan-and-zoom canvas;
- clustered document, evidence, and artifact nodes;
- labelled assertion edges;
- node search with whitespace normalization;
- relationship-type filtering;
- node and edge selection;
- stable-key, object-ID, confidence, review-status, edge-ID, and provenance
  inspection;
- explicit truncation warning and graph totals.

The similarity to Obsidian is visual and interaction-oriented. ResearchOS keeps
its scientific trust boundary: graph data is loaded from the canonical backend,
the default query is `review_status=accepted`, and the UI does not infer or
promote scientific status.

## Actual browser acceptance

- Default accepted-only view: 84 nodes and 160 edges.
- The backend reported truncation at the configured 160-edge display limit.
- Search for `demographic control` normalized PDF line breaks and returned the
  expected two-node, one-edge source context.
- The selected evidence node exposed stable key
  `evidence:object-a369437ab603049f6edddf86`.
- The selected `contains` edge exposed accepted status, confidence `0.75`,
  provenance `1d87edcf-c388-4f0d-96f7-7481041ba90c`, and its canonical edge ID.
- Zoom controls, fit reset, canvas pan handlers, search, filtering, and refresh
  were present and interactive.

## Verification

- Canonical UI behavior tests: 8 passed.
- Canonical Vinext production build: passed.
- Browser semantic and visual inspection: passed.

## Decision

Canonical graph inspection is accepted locally as the next Stage 5 UI
capability. Theory construction remains gated: a graph view is an assertional
representation, not a declaration that a theory or evidence item is true.
