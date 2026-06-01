# AI Learning Loop

The AI learning loop is a local, evidence-backed memory service. It helps the app remember useful patterns without turning weak signals into business claims.

The service lives in `scripts/services/ai_memory.py`.

## What It Learns From

`AIMemoryService.refresh_from_local_evidence()` can create or refresh memory from:

- Active `content_insights` produced from local analytics.
- Draft approval logs.
- Draft rejection, revision, and reapproval logs.
- Local reply approval, rejection, escalation, spam, and manual-handling audits.

Memory records use stable IDs for derived evidence. Running the refresh twice updates the same records instead of creating duplicate learning noise.

## Evidence And Privacy

Each derived memory stores evidence IDs and counts. Engagement learning stores `reply_approvals` IDs, not private comment or message text.

Every memory includes:

- A memory type.
- A short title.
- A plain-language summary.
- Evidence references.
- Confidence: `low`, `medium`, or `high`.
- Source provenance.
- Status: `active`, `archived`, or `superseded`.

Mock analytics produce `source = mock` memory. A mock-derived memory must stay visibly mock throughout the loop.

## Generation Context

When the Generate screen runs through the localhost bridge, the content
generation service loads up to eight active memory records for the selected
brand. It passes bounded title, summary, confidence, type, and source fields
into the prompt context and records the same safe summaries in prompt
metadata.

Raw engagement content is not added to the prompt through this loop. Memory is
guidance, not a new business claim, and generated drafts still require owner
review.

## Conservative Behavior

The learning loop does not:

- Call an external AI provider.
- Call social platform APIs.
- Send replies.
- Publish posts.
- Delete memory automatically.
- Treat owner approval as proof of performance.
- Turn a small sample into a guarantee.

Manual memory can be archived without deleting its audit value.

## Run A Local Refresh

```text
python -m scripts.services.ai_memory --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care
```

The command prints the refreshed records and explicit `external_ai_calls=false` and `external_platform_calls=false` markers.

## Review Memory In The App

Open Analytics and use **Weekly review and AI memory**. The owner can refresh
memory from local evidence, inspect the active summaries used by future draft
generation, and archive a record without deleting it.

Superseding a memory record remains future work.
