# Local Canonical Workflow Case Acceptance

Date: 2026-07-20  
Verification time: 22:44–22:57 WITA  
Environment: local ResearchOS Docker stack and `http://localhost:3000/`  
Decision: **ACCEPTED LOCALLY**

## Scope

This acceptance covers the first canonical research-workflow case read model
and UI progression. The projection joins immutable discovery snapshots to the
existing PostgreSQL scientific ledgers and displays the next governed action.
It creates no scientific decision, lifecycle authority, or automated
transition.

## Implemented contract

- Authenticated project workflow-case list and detail endpoints.
- Discovery snapshot recovery after API restart.
- Explicit preservation, but no promotion, of pre-contract discovery history.
- Record-bound projection through acquisition, inspection, screening,
  extraction, evidence review, knowledge intake, and graph creation.
- Graph-bound projection of theory bundles, active validations, and immutable
  publication packages.
- Canonical UI timeline with `complete`, `pending`, and `blocked` states.
- Required-role display for discoverer, reviewer, indexer, and publisher.
- Explicit `derived_read_model_only` authority and
  `decision_automation: false`.

## Failed observation preserved

The first rebuilt API failed closed during startup. Historical pre-contract
snapshots use an older shape without `discovery_contract`,
`source_definitions`, or provider `enumerations`. The initial recovery loader
attempted to interpret them as current governed snapshots and raised
`KeyError: discovery_contract`.

The correction identifies the canonical shape before reconstruction.
Integrity-valid pre-contract files remain unchanged as historical evidence,
are counted as unsupported, and are not exposed as governed workflow cases.
Hash corruption or identity mismatch still prevents startup.

## Automated verification

- Discovery persistence and compatibility tests: 23 passed.
- Targeted workflow API tests: 41 passed.
- Final full backend regression after the compatibility correction: 534 passed.
- Canonical UI build: passed.
- Canonical UI behavior and contract tests: 15 passed.
- Source diff check: passed.

## Local runtime verification

The API and worker were rebuilt from the changed local source. PostgreSQL and
MinIO retained their existing volumes. The rebuilt API became healthy and
successfully reopened current discovery snapshots after restart.

The canonical UI was opened through the actual local browser and authenticated
with the local reviewer account. The workflow surface displayed 39 governed
discovery cases. The selected acceptance case was:

`discovery-fe93564b17ed46f19c917291c57f1077`

Research question:

`Apa temuan ilmiah pada artikel DOI 10.3389/fdata.2022.971974?`

Displayed progression:

1. discovery complete: one unique record;
2. acquisition complete: one representation;
3. inspection and screening complete: one eligible source;
4. extraction complete: five provisional objects;
5. evidence review complete: one accepted and zero pending in the latest
   canonical extraction;
6. knowledge intake complete: one graph;
7. proposition and theory pending;
8. validation blocked; and
9. publication blocked.

The UI correctly identified reviewer authority as the next governed role and
did not create a proposition, theory, validation, or publication.

## Refresh and database persistence

After a full browser reload:

- the authenticated session remained valid;
- the same workflow case was restored;
- the five-object extraction remained visible;
- the accepted-evidence graph remained visible; and
- proposition and theory remained the next governed action.

PostgreSQL independently confirmed the latest extraction:

- extraction:
  `extraction-3f7b46f6955d6422fadaacee`;
- object count: 5;
- current accepted count: 1;
- current pending count: 0; and
- graph:
  `graph-153e3c4ffedf972b718bf9cb`.

The database also retains a disclosed historical duplicate extraction and its
five objects. The read model selects the latest canonical extraction and does
not erase or misrepresent the historical batch.

## Decision boundary

The workflow projection is accepted locally through the current graph and
blocker. Completing the full golden path still requires an authorized human
decision on a graph-bound cross-study proposition, followed by theory,
validation, publication preview, and publisher release. This acceptance does
not make those decisions.

No VPS or production target was accessed or changed during this local
acceptance.
