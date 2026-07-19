# ResearchOS Local Browser Acceptance Report

Date: 2026-07-19
Scope: local one-machine workspace
Decision: **ACCEPTED — BASIC DISCOVERY FLOW**

## Executed workflow

The canonical workspace at `http://127.0.0.1:8080/workspace` was exercised
through the in-app browser using the local Discoverer account:

1. login with the local human workspace session;
2. select the default `ResearchOS` project;
3. open **Penelusuran & Ingesti**;
4. submit a bounded discovery with one OpenAlex provider and one requested
   result;
5. receive the article **Open science, reproducibility, and transparency in
   ecology**;
6. log out;
7. log in again; and
8. verify the local project and its object inventory remain available.

The accepted research question was:

> Bagaimana praktik open science mendukung reproduksibilitas penelitian?

The corresponding discovery run was verified in the local
`knowledge_data` volume after the browser session. No credential, cookie,
CSRF value, or provider response payload is recorded in this report.

## Defects found and fixed

Interactive acceptance exposed that the workspace submitted the legacy
discovery payload while the backend requires a governed discovery contract
and human-attributed query concepts. It also treated `state.project` as an
object even though the canonical workspace stores it as a project-ID string.
The resulting HTTP 422 validation details were rendered as
`[object Object]`.

The fix:

- binds the question, search plan, project, and discovery contract IDs;
- supplies bounded source, inclusion, exclusion, language, document,
  evidence, depth, budget, license, review, and stopping policies;
- supplies a human-attributed query concept;
- renders structured validation messages as readable text; and
- versions the corrected JavaScript asset URLs to prevent stale browser code.

## Decision

The basic local browser discovery flow is accepted. Authentication, governed
discovery submission, provider result rendering, logout, login renewal, and
local run persistence were observed on the running one-machine installation.

Document acquisition, extraction, evidence review, and publication remain
separate role-governed acceptance flows and are not implied by this decision.
