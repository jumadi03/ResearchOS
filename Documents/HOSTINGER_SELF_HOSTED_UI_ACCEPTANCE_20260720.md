# ResearchOS Self-Hosted UI Acceptance — Hostinger

Date: 2026-07-20  
Production target: `https://researchos.click`  
VPS IPv4: `76.13.20.211`  
Backend target: `https://api.researchos.click`  
Decision: **ACCEPTED FOR SELF-HOSTED UI CONNECTIVITY AND SESSION PERSISTENCE**

## Scope

This acceptance verifies that the canonical ResearchOS UI is served by the
ResearchOS stack on the real Hostinger VPS, reaches the production backend,
supports human login, and preserves the authenticated session after a browser
refresh. It is separate from release-candidate acceptance and does not change
the rejected status of `v0.5.0-rc.2`.

## Deployed revisions

- Production stack commit:
  `52409f2abd3289c190ef17216f5aa89aa06d5bf0`
- Initial self-hosted UI commit:
  `a8ae95d05ff2ca794726597e73bc23b4757860f2`
- Corrective UI commit:
  `def1c7831a05e7f4d1bdd676630f12192c16b4ac`
- Running UI image:
  `researchos-ui:def1c7831a05e7f4d1bdd676630f12192c16b4ac`
- Runtime state after deployment: `running/healthy`

## DNS and HTTPS evidence

- The public result for `researchos.click` resolved to `76.13.20.211`.
- `www.researchos.click` remained a CNAME alias of `researchos.click`.
- The first ACME attempt failed because Let's Encrypt still observed the former
  Hostinger parking address `2.57.91.91`.
- After DNS propagation, Traefik was restarted to request a new certificate.
- A strict HTTPS request to `https://researchos.click/` then returned HTTP 200
  without bypassing certificate validation.
- `https://www.researchos.click/` returned HTTP 200.
- The unauthenticated same-origin session proxy returned the expected HTTP 401
  backend response.

## Failed observation and correction

The first real login attempt returned HTTP 500. Production UI logs recorded:

```text
TypeError: RequestInit: duplex option is required when sending a body.
```

The UI proxy constructed a Node `Request` from a streaming request body without
setting the required `duplex: "half"` option. The corrective commit applies the
option only when a body exists and adds a regression test for a POST login body
through the explicitly permitted internal Docker API.

After correction:

- the Vinext production build passed;
- all 13 UI tests passed;
- the corrected image was built on the VPS from the committed source;
- the UI container was replaced without replacing the backend or database; and
- a public login request with deliberately invalid test credentials reached the
  backend and returned HTTP 401 instead of HTTP 500.

No real credential, session token, CSRF token, or password was recorded.

## Human and database acceptance

The user completed a real login at `https://researchos.click` and visually
confirmed:

- status `TERHUBUNG`;
- `SESSION TERVERIFIKASI`;
- reviewer identity and role;
- canonical project/lifecycle content; and
- the canonical knowledge graph.

The user then pressed F5. The browser remained authenticated and reloaded the
production project and graph data instead of returning to the login form.

PostgreSQL production metadata confirmed the same active reviewer session:

```text
created_at  = 2026-07-20 07:14:21.605749+00
last_seen_at before refresh = 2026-07-20 07:14:55.640642+00
last_seen_at after refresh  = 2026-07-20 07:17:03.982460+00
expires_at  = 2026-07-20 19:14:21.597799+00
revoked_at  = NULL
```

This proves persistence across the public UI, production backend, and
production PostgreSQL database.

## Evidence files supplied by the user

- `C:\Users\ROG\Pictures\Screenshots\Screenshot 2026-07-20 145445.png`
  — DNS root record points to the VPS.
- `C:\Users\ROG\Pictures\Screenshots\Screenshot 2026-07-20 150149.png`
  — self-hosted login UI at `researchos.click`.
- `C:\Users\ROG\Pictures\Screenshots\Screenshot 2026-07-20 150343.png`
  — preserved failed HTTP 500 observation.
- `C:\Users\ROG\Pictures\Screenshots\Screenshot 2026-07-20 151440.png`
  — successful verified reviewer session.
- `C:\Users\ROG\Pictures\Screenshots\Screenshot 2026-07-20 151741.png`
  — project and graph remain loaded after F5.

## Decision boundary

Self-hosted UI connectivity and authenticated-session persistence are accepted.
The existing Sites deployment remains a fallback and is not production evidence
for this decision.

The broader canonical mutation acceptance remains a separate controlled step:
perform one safe audited mutation, refresh, and match the resulting audit event
and production database record. No acceptance-only mutation was performed as
part of this infrastructure cutover.
