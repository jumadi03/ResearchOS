# ResearchOS Support

ResearchOS is an experimental open-source project maintained on a best-effort
basis. There is no guaranteed response time, uptime, data recovery, or
compatibility support. The current supported development target is the latest
revision of `main`; public releases are immutable reproducibility references.

## Start here

Before opening an issue:

1. read [ResearchOS in 5 Minutes](Documents/GETTING_STARTED.md);
2. check the [first research workflow](Documents/FIRST_RESEARCH_WORKFLOW.md);
3. search existing [GitHub Issues](https://github.com/jumadi03/ResearchOS/issues);
4. retry with the unmodified public release or latest `main`; and
5. remove credentials, personal data, private research content, and copyrighted
   documents from all evidence.

## Choose the correct channel

| Need | Where to report |
| --- | --- |
| Reproducible software defect | [Bug report](https://github.com/jumadi03/ResearchOS/issues/new?template=bug_report.yml) |
| Scoped product or engineering improvement | [Feature request](https://github.com/jumadi03/ResearchOS/issues/new?template=feature_request.yml) |
| Incorrect, unclear, or missing documentation | [Documentation report](https://github.com/jumadi03/ResearchOS/issues/new?template=documentation.yml) |
| Vulnerability, exposed credential, or sensitive-data leak | [Private security report](https://github.com/jumadi03/ResearchOS/security/advisories/new) |

Never report a vulnerability or exposed secret in a public issue.

## A useful bug report

Include only sanitized information:

- ResearchOS version or commit;
- operating system, Python version, and Docker Desktop version;
- the smallest repeatable sequence that demonstrates the problem;
- expected and actual behavior;
- the name of the failing service or quality gate; and
- minimal logs with all credentials, tokens, local paths, personal data, and
  private research material removed.

Do not upload `deploy/stack.env`, `deploy/local-access.env`,
`deploy/monitoring/prometheus.token`, `.env`, database dumps, MinIO objects, or
unredacted screenshots.

## Scope boundaries

Maintainers can help assess reproducible ResearchOS behavior. They cannot
provide scientific peer review, professional or regulatory advice, recover
unknown local credentials, determine document licensing, or support unsafe
internet-facing deployments based on the local development stack.

AI-generated output remains advisory and must be reviewed by a qualified human.

