# ResearchOS Real-Environment Acceptance Policy

Date adopted: 2026-07-20

## Purpose

This policy prevents simulations, local tests, and restore drills from being
mistaken for evidence that ResearchOS works in production.

## Canonical targets

| Level | Canonical target | Accepted purpose |
|---|---|---|
| Production UI | `https://researchos-ilmiah.jumadi03.chatgpt.site/` | User-visible production acceptance |
| Production API | `https://researchos-api.srv1534304.hstgr.cloud` | Live backend acceptance |
| Production VPS | Hostinger `srv1534304`, `76.13.20.211` | Infrastructure and service evidence |
| Production database | PostgreSQL `researchos` on Hostinger | Persistence and canonical-data evidence |
| Production storage | MinIO on Hostinger | Object-storage evidence |
| Local computer | `D:\ResearchOS` and local services | Source, backup, development, and preliminary testing |

Local results do not prove production behavior.

## Evidence required

A production claim is accepted only when the report contains:

- verification time;
- exact environment and target;
- actual state before the operation;
- the operation performed;
- actual state after the operation;
- refresh or new-session persistence evidence;
- matching production API or database evidence; and
- the user's confirmation for visible UI behavior.

Evidence must come from the public UI, live Hostinger service, or production
database as appropriate. Mock data, fixtures, screenshots of local URLs,
isolated restore drills, and local containers must be labeled accurately.

## Completion language

Use these terms precisely:

- **Simulated:** exercised with examples, mocks, fixtures, or isolated test
  systems.
- **Local verified:** proven on the user's computer only.
- **Production reachable:** the real service responds, without proving the
  complete workflow.
- **Production accepted:** the real end-to-end workflow and persistence have
  been verified against production data.

Authentication reachability is not mutation acceptance. A successful response
is not persistence acceptance until the result survives reload and matches the
production database.

## Conflict and correction

If the user's screen conflicts with an automated report, record the conflict as
a production finding and inspect the live system again. Correct reports by
appending a dated finding; do not rewrite history to hide an earlier incorrect
claim.

## Current acceptance gate

The next end-to-end gate is:

1. authenticate through the public production UI;
2. open a real production project;
3. record the relevant production database state;
4. perform one safe, reversible mutation;
5. reload the public UI;
6. verify that the result persists;
7. match it to the production database; and
8. record the user's visual confirmation.
