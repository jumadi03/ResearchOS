# ResearchOS Live Production Evidence

Verification time: `2026-07-20T03:49:17Z`

## Scope

This evidence was collected from the public ResearchOS Sites deployment and a
fresh key-only SSH session to the Hostinger VPS. It is not a local simulation
or isolated restore drill.

## Public UI observation

Before remediation, a fresh browser inspection of
`https://researchos-ilmiah.jumadi03.chatgpt.site/` displayed:

- `Backend belum tersedia`;
- `LAYANAN BELUM TERHUBUNG`; and
- a message that `RESEARCHOS_API_ORIGIN` was not configured.

This contradicted the earlier UI acceptance statement.

The Sites runtime environment contained
`RESEARCHOS_API_ORIGIN=https://researchos-api.srv1534304.hstgr.cloud`, but the
active deployment had not applied environment revision 1. Sites version 9 was
therefore republished. Deployment
`appgdep_6a5d9a730c888191a59f2ded3160ef7a` completed with status `succeeded`
and `env_set_revision=1`.

After a browser reload, the UI changed to:

- status `Belum masuk`;
- panel `MASUK KE WORKSPACE`;
- heading `Gunakan akun ResearchOS Anda`; and
- username and password controls.

This is the expected unauthenticated boundary returned when the public UI can
reach the configured ResearchOS backend.

## Hostinger VPS evidence

The fresh remote session reported:

```text
VERIFIED_AT_UTC
2026-07-20T03:49:17Z
HOST
srv1534304
BOOT_ID
91a312bd-6913-4440-8994-3ded6b25b16a
PUBLIC_IP
76.13.20.211
API_HEALTH
{"status":"ok"}
DATABASE_FACTS
researchos|41|325|6
```

The database fields are, in order:

- database: `researchos`;
- schema version: `41`;
- canonical objects: `325`; and
- workspace users: `6`.

The production monitor reported:

```json
{
  "checked_at": "2026-07-20T03:48:21.647141+00:00",
  "status": "passed",
  "checks": [
    {"name": "api", "status": "passed"},
    {"name": "minio", "status": "passed"},
    {
      "name": "postgresql",
      "status": "passed",
      "schema_version": 41,
      "canonical_object_count": 325
    }
  ],
  "failures": []
}
```

The latest completed backup manifest remained:

```text
/backups/backup-set-20260720T031629Z.json
```

## Security evidence

The effective SSH policy reported:

```text
maxauthtries 3
permitrootlogin no
passwordauthentication no
kbdinteractiveauthentication no
allowusers ubuntu
```

UFW reported `Status: active` and allowed only ports 22, 80, and 443 for IPv4
and IPv6.

## Decision

The initial browser observation was a real production defect and invalidated
the prior claim that the UI was connected at that moment. After republishing
Sites version 9 with environment revision 1, the public UI reached the real
backend authentication boundary. The Hostinger backend, canonical database,
monitor, backup, and security controls were independently verified from the
live VPS.

Authenticated mutation acceptance remains a separate test and must not be
inferred solely from the unauthenticated login boundary.
