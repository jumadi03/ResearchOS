# Local Canonical Graph Explorer Acceptance Report

Date: 2026-07-20  
Environment: `http://localhost:3000/` and local ResearchOS API  
Result: Accepted locally

## Design outcome

The canonical UI now includes an Obsidian-inspired knowledge atlas:

- dark pan-and-zoom canvas;
- clustered document, evidence, and artifact nodes;
- contextual assertion-edge labels and direction markers;
- node search with whitespace normalization;
- relationship-type, node-type, review-status, and confidence filtering;
- keyboard-accessible node and edge selection;
- one-hop subgraph focus with incoming/outgoing summaries;
- stable-key, object-ID, confidence, review-status, edge-ID, and provenance
  inspection;
- deep links into the audited Object Inspector;
- an expandable nonvisual relationship list;
- project-scoped persistence of filters, focus, selection, zoom, and pan;
- responsive tablet and mobile layouts;
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
- Confidence `0.90+` reduced the accepted-only view to 28 nodes and 38 edges.
- The expandable relationship list exposed the same 38 filtered relations and
  selected an accepted edge into the inspector.
- One-hop focus reduced the default example from 84 nodes and 160 edges to 2
  nodes and 1 edge, then restored the full graph deterministically.
- The full graph rendered zero visible relationship labels; selecting the
  example node revealed only its contextual `contains · 0.75` label.
- All 160 visible edges exposed keyboard button semantics, complete accessible
  names, and Enter/Space selection.
- Mobile verification used a 390-pixel viewport contract: the graph canvas
  resolved to 430 pixels high with one-column controls and no horizontal
  overflow.
- Tablet verification used a 768-pixel viewport contract: the graph canvas
  resolved to 540 pixels high with two-column controls and no horizontal
  overflow.
- After setting confidence `0.90+` and focusing an evidence node, refresh
  restored the same 4-node, 3-edge subgraph, selected node, and inspector
  state.

## Verification

- Canonical UI behavior tests: 8 passed.
- Canonical Vinext production build: passed.
- Browser semantic, keyboard, responsive, persistence, and visual inspection:
  passed.
- Full backend regression: 505 passed, 0 failed in 33.36 seconds.
- The first backend invocation used the inaccessible global Windows pytest
  temp root and produced fixture setup errors. Repeating the identical suite
  with an isolated workspace `--basetemp` removed every setup error; this was
  an environment correction, not a source-code change.

## Decision

Canonical graph inspection is accepted locally as the next Stage 5 UI
capability. Theory construction remains gated: a graph view is an assertional
representation, not a declaration that a theory or evidence item is true.
