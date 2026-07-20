# ResearchOS Working Agreement

## Commit, deploy, and production-proof workflow

ResearchOS implementation work must not stop at a local commit. For each
approved production change:

1. implement and test the change on the local ResearchOS source;
2. create an intentional Git commit containing only the approved scope;
3. deploy that exact committed source to the ResearchOS services on Hostinger;
4. verify the deployed revision on the real Hostinger VPS;
5. verify the corresponding behavior through the public production UI or API;
6. verify persistence in the production database when the change affects data;
   and
7. preserve timestamped before-and-after evidence in an acceptance report.

The Hostinger deployment is production evidence, not a replacement Git remote.
The commit remains in the ResearchOS Git repository, while the exact committed
revision is deployed to Hostinger and its running revision is recorded.

This workflow authorizes deployment and verification of ResearchOS. It does not
authorize changes to n8n, WAHA, unrelated VPS services, billing, ownership,
domain registration, or unrelated DNS configuration unless the user requests
those changes explicitly.

## Real-environment acceptance rule

All future ResearchOS work must distinguish clearly between simulation, local,
staging, and production. Never present a local test, mock, fixture, restore
drill, or simulated result as proof of production behavior.

The canonical real targets are recorded in
`deploy/production-registry.json`. The current targets are:

- Public production UI:
  `https://researchos.click/`
- Production backend:
  `https://api.researchos.click`
- Production VPS:
  Hostinger host `srv1534304`, public IP `76.13.20.211`
- Production database:
  PostgreSQL database `researchos` on the Hostinger VPS
- Production object storage:
  MinIO on the Hostinger VPS
- Local computer:
  source code, off-VPS backups, development, and preliminary tests only

Historical Sites and Hostinger service URLs may remain available as aliases or
fallbacks, but they are not the canonical acceptance targets unless the
production registry is changed by an attributable operational decision.

Production acceptance requires evidence collected from the real target:

1. record the verification time and exact target;
2. capture the actual state before and after the operation;
3. verify the public UI through its production URL;
4. verify the corresponding result in the production backend or database;
5. reload the UI or sign in again and prove persistence;
6. preserve evidence in a dated report; and
7. obtain the user's visual confirmation when the acceptance includes UI
   behavior.

Do not declare production work complete merely because:

- local or simulated tests pass;
- a container is running;
- a health endpoint responds;
- the login form is visible; or
- a mutation returns success without refresh and database verification.

If observations conflict, treat the user's visible production observation as a
finding, re-check the live system, and correct the acceptance report
transparently. Never erase a failed observation from the audit history.

The next required end-to-end production acceptance is:

`public login -> real project -> one safe mutation -> reload -> production
database match`.
