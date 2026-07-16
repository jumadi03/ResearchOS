# Your First ResearchOS Workflow

This guided demo turns a research question into a deduplicated literature
snapshot with source provenance. It uses the browser workspace, takes about
five minutes after ResearchOS is running, and does not require an AI-provider
API key.

## What you will create

You will search two public scholarly providers for literature about
reproducible research. ResearchOS will preserve the provider records, merge
matching results without erasing their sources, and create a versioned metadata
snapshot.

The result is a discovery record, not validated scientific evidence. Human
review and document verification remain separate steps.

## Before you begin

Complete [ResearchOS in 5 Minutes](GETTING_STARTED.md). Confirm that the API
health page at <http://127.0.0.1:8080/health> responds successfully.

Open `deploy/local-access.env` on your own computer and locate these two lines:

```text
RESEARCHOS_DISCOVERER_USERNAME=...
RESEARCHOS_DISCOVERER_PASSWORD=...
```

Keep the file private. Do not copy its values into an issue, chat, screenshot,
commit, or pull request.

## 1. Sign in to the workspace

![ResearchOS workspace login with empty credential fields](images/researchos-workspace-login.png)

1. Open <http://127.0.0.1:8080/workspace>.
2. Enter the discoverer username and password from `deploy/local-access.env`.
3. Select **Masuk**.
4. Confirm that the status in the upper-right corner changes to **Terhubung**.

The browser stores the session in an HttpOnly cookie. The password is sent only
to the loopback-bound local ResearchOS service.

## 2. Define a small discovery run

Select **Discover** in the left navigation and enter:

| Field | Demo value |
| --- | --- |
| Research question | How do open-science practices improve the reproducibility of scientific research? |
| Search query | open science reproducibility research |
| Literature providers | OpenAlex and Crossref |
| Results per provider | 5 |
| Year from | 2020 |
| Year to | 2026 |

Select **Run discovery**. ResearchOS contacts the selected providers, records
their responses and provenance hashes, and deduplicates matching publications.

Public-provider availability and results can change. A provider failure is
shown explicitly and does not get silently converted into a successful result.
If both providers are temporarily unavailable, wait briefly and retry.

## 3. Read the discovery result

The summary shows:

- **unique records**: publications remaining after deterministic matching;
- **provider failures**: providers that did not return a usable response; and
- **schema**: the version used to interpret the snapshot.

Each literature card retains its provider identity and the number of source
records that contributed to the merged result. A match does not erase the
underlying source observations.

## 4. Create the metadata snapshot

Select **Collect metadata** once. A successful run changes the button to a
versioned confirmation with the provider-observation count, such as
`Metadata v1.0 · 2 observations`. The confirmation message also reports
citation edges; an empty result is identified explicitly instead of appearing
as an ordinary enrichment success.

This step preserves normalized observations, citations, metadata conflicts,
and correction or retraction signals separately from the original discovery
snapshot. Repeating an identical operation is designed to be idempotent rather
than creating conflicting canonical records.

## 5. Interpret the result safely

At this point you have demonstrated:

- role-gated literature discovery;
- explicit provider-failure handling;
- deterministic record matching;
- source and response-hash provenance; and
- versioned metadata collection.

You have not yet demonstrated that a paper is trustworthy, that a claim is
accepted evidence, or that a generated theory is correct. ResearchOS keeps
document acquisition, evidence extraction, reviewer decisions, validation,
and publication as explicit later stages.

## Optional next step: acquire an open document

Only continue when a result has a direct HTTPS PDF URL, an explicit open-access
status, and a known license.

1. Select **Acquire** on that result.
2. Enter the direct PDF URL.
3. Keep **Access status** set to **Open** only when that is verifiably true.
4. Enter the declared license, for example `CC-BY-4.0`.
5. Select **Acquire & verify**.

ResearchOS rejects missing provenance, invalid PDF content, checksum conflicts,
and unknown or restricted access instead of guessing. Do not bypass copyright
or access restrictions for a demo.

## Finish the demo

Use **Ganti akses** and log out when you are finished. To stop the local stack
without deleting its data, follow the safe shutdown instructions in
[ResearchOS in 5 Minutes](GETTING_STARTED.md#5-stop-safely).
