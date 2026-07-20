# ResearchOS Working Agreement

## Real-environment acceptance rule

All future ResearchOS work must distinguish clearly between simulation, local,
staging, and production. Never present a local test, mock, fixture, restore
drill, or simulated result as proof of production behavior.

The canonical real targets are:

- Public production UI:
  `https://researchos-ilmiah.jumadi03.chatgpt.site/`
- Production backend:
  `https://researchos-api.srv1534304.hstgr.cloud`
- Production VPS:
  Hostinger host `srv1534304`, public IP `76.13.20.211`
- Production database:
  PostgreSQL database `researchos` on the Hostinger VPS
- Production object storage:
  MinIO on the Hostinger VPS
- Local computer:
  source code, off-VPS backups, development, and preliminary tests only

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
