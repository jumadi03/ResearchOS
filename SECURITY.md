# Security Policy

## Supported version

ResearchOS is under active development. Security fixes are applied to the
latest revision of the `main` branch; older commits and local modifications are
not separately supported.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability, exposed credential,
or sensitive research data. Use GitHub's private vulnerability reporting:

https://github.com/jumadi03/ResearchOS/security/advisories/new

Include affected components, reproduction conditions, impact, and any safe
mitigation you have identified. Remove real credentials, personal data,
copyrighted research documents, and production data from the report.

You should receive an acknowledgement within seven days. Validation and
remediation timelines depend on severity and reproducibility. Please allow a
coordinated fix before public disclosure.

## Operational expectations

- Bind local services to loopback unless a hardened deployment is designed.
- Generate unique credentials and store them only in ignored local files or a
  suitable secret manager.
- Rotate any credential that appears in a terminal recording, screenshot,
  issue, log, or commit.
- Preserve authentication, authorization, provenance, and append-only audit
  boundaries when extending the system.
- Do not use development defaults for an internet-facing deployment.
