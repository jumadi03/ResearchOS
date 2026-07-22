# SGF-020 Canonical Admission Record

## Decision

- Document ID: `SGF-020`
- Official title: `Human Authority & Decision Matrix`
- Version: `1.0`
- Decision: `ratified`
- Publication status: `Published Canonical Edition`
- Classification: `Scientific Governance Standard`
- Human authority and ratifier: `Jumadi`
- Decision date: `2026-07-19`
- Prior state: `draft_for_human_review`
- Resulting state: `ratified_and_published`
- Decision basis: explicit project-owner agreement with the recommendation to
  ratify the exact SGF-020 v1.0 candidate

## Reviewed candidate

- File:
  `Documents/Candidates/SGF-020_Human_Authority_Decision_Matrix_v1.0_Draft_for_Human_Review.md`
- SHA-256:
  `3dfe92945cd921c637b79201bc444ae533ffb02c856518b6f86836be73ec1109`
- Review packet:
  `Documents/Candidates/SGF-020_v1.0_HUMAN_REVIEW_PACKET.md`
- Review result:
  `passed; recommended for explicit human ratification with activation qualification`

## Historical source

- File:
  `Documents/SGF_020_HUMAN_AUTHORITY_DECISION_MATRIX.md`
- SHA-256:
  `e51beac2b7ea3d6d4e4543ec7be4e6b7e0b905614543b3cea1a566a85b47d387`
- Preservation rule:
  the historical working source remains unchanged and non-canonical

## Canonical representation

- File:
  `Documents/SGF-020_Human_Authority_Decision_Matrix_v1.0_Published_Canonical_Edition.docx`
- SHA-256:
  `e3b9487931f6fbab81253f26dd9e4f27c3d35e6ea5243cd9f015ec15d72f71c0`
- File size: `48076 bytes`
- Format:
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Page count: `13`
- Integrity rule:
  the representation is canonical only while its byte hash matches the value above

## Verification

- Visual QA: `passed, 13/13 pages inspected`
- Accessibility audit: `passed, 0 findings`
- Structural audit: `passed; no placeholders, comments, or tracked changes`
- Table rendering:
  `passed; repeated headers, intact rows, and portrait/landscape transitions verified`
- Named style overrides:
  `cover typography, table-cell typography and geometry, list numbering,
  landscape decision matrix, and page furniture`

Style lint reports 122 directly formatted runs and 249 directly formatted
paragraphs because the named overrides above are encoded explicitly. Visual
inspection found no unexplained drift, clipping, overlap, orphan headings, or
split decision rows.

## Authority, scope, and activation qualification

SGF-020 establishes the normative authority model for human scientific
decisions, decision admission, separation of duties, appeal, correction,
supersession, invalidation, rollback, and AI restrictions.

Ratification does not prove that every required control is implemented. Full
SGF-020 compliance for consequential medical, legal, safety-critical,
human-subject, or regulatory research must not be claimed until the required
extensions are implemented and verified. Missing authority or safety controls
must fail closed.

This is a project-owner governance decision. It is not independent peer review
or scientific validation.

## Dependency effect

SGF-030 is now the next eligible canonicalization target. SGF-040 remains
blocked until SGF-030 is separately reviewed, ratified, and published.

## Change rule

The canonical representation is immutable. Any byte-changing correction
requires a new representation, hash, and correction record. A substantive
change requires a new version and decision record that preserves this version
and links the successor, authority, rationale, date, and hashes.
