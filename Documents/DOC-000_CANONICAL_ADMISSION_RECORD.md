# DOC-000 Canonical Admission Record

## Decision

- Document ID: `DOC-000`
- Official title: `Standar Publikasi Dokumen Kanonik`
- Project: `Proyek Teori Ruang Orientasi`
- Version: `0.2`
- Decision: `ratified`
- Publication status: `Published Canonical Edition`
- Classification: `Project Governance Publication Standard`
- Human authority and ratifier: `Jumadi`
- Decision date: `2026-07-19`
- Prior state: `candidate_pending_human_review`
- Resulting state: `ratified_and_published`
- Decision basis: explicit project-owner instruction to make the reviewed
  DOC-000 v0.2 candidate a canonical ResearchOS document

## Reviewed candidate

- Candidate file:
  `Documents/Candidates/DOC-000_Standar_Publikasi_Dokumen_Kanonik_v0.2_Draft_for_Human_Review.docx`
- Candidate SHA-256:
  `9258d43f59344bd5c6432376e00bc089f8a8152c64d6e1ebfe41c75518217776`
- Review packet:
  `Documents/Candidates/DOC-000_v0.2_HUMAN_REVIEW_PACKET.md`
- Review result:
  `all six stated review criteria passed`

The publication representation changes only publication packaging and
metadata: status, ratification provenance, canonical effect, and revision
history. It does not change the reviewed normative rules.

## Canonical representation

- File:
  `Documents/DOC-000_Standar_Publikasi_Dokumen_Kanonik_v0.2_Published_Canonical_Edition.docx`
- SHA-256:
  `df0f0613af407bc9a77780a516b33386159bd6da2dba255f6030dde90cc8e593`
- Format:
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Page count:
  `6`
- Integrity rule:
  the file is canonical only while its byte hash matches the value above

## Verification

- Visual QA: `passed, 6/6 pages inspected`
- Accessibility audit: `passed, 0 findings`
- Style lint:
  `passed, 0 direct run-formatting and 0 direct paragraph-formatting findings`
- Structural audit:
  `passed; no placeholders, comments, or tracked changes`
- Numbering audit:
  `passed; distinct numbered lists begin at 1`

## Authority and scope

DOC-000 v0.2 governs publication of canonical project-governance documents
within its stated scope. It does not replace scientific review, accept
evidence, define scientific ontology, or convert publication into scientific
truth.

This ratification is a project-owner governance decision. ResearchOS has not
demonstrated an independent human governance reviewer, so the decision must not
be represented as independent peer review or scientific validation.

DOC-001 v1.0 remains a valid canonical transitional artifact. DOC-000 does not
invalidate it retroactively. A separate gap assessment may add
non-substantive metadata through a manifest; substantive change requires a new
DOC-001 version.

## Provenance

1. DOC-000 v0.1 was preserved byte-identically as a non-canonical candidate.
2. Its incomplete operational coverage and visual defects were documented.
3. DOC-000 v0.2 expanded the standard and corrected the numbering and layout.
4. The exact v0.2 candidate was rendered, audited, and reviewed against
   DOC-001 and SGF-020, SGF-030, and SGF-040.
5. The human authority explicitly approved canonical admission.
6. A separate Published Canonical Edition was generated, rendered, audited,
   and frozen by the canonical hash above without overwriting either candidate.

## Change rule

The canonical representation is immutable. Any correction or metadata change
that changes its bytes requires a new representation, a new hash, and an
explicit correction record. A substantive amendment or supersession requires
a new version and decision record preserving this version, the reason,
authority, date, and relationship to the successor.
