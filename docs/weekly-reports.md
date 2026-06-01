# Weekly Reports

Weekly reports are deterministic local summaries built from analytics snapshots. They help the owner review performance without requiring live platform analytics.

The service lives in `scripts/services/weekly_reports.py`.

## Report Contents

Each report stores:

- Brand Brain ID.
- Week start and end dates.
- Plain-language summary.
- Wins.
- Concerns.
- Recommendations.
- Top local posts.
- Platform breakdown.
- Metric totals and source labels.
- Generator label: `system`, `ai_mock`, `ai_provider`, or `manual`.

The current generator uses only local deterministic logic. It does not call an AI provider.

## Provenance

Mock-only weeks use:

```text
generated_by = ai_mock
metricTotals.demo = true
metricTotals.sources = ["mock"]
```

Weeks with no snapshots get an honest empty summary. Manual and future imported data retain their source labels.

## Idempotency

Each brand and week has one stable generated report ID. Regenerating a week updates that report instead of creating duplicates.

## Generate A Report

```text
python -m scripts.services.weekly_reports --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care --week-start-date 2026-06-08
```

Optional source filter:

```text
python -m scripts.services.weekly_reports --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care --week-start-date 2026-06-08 --source manual
```

## Review Reports In The App

Open Analytics and use **Weekly review and AI memory**. Choose a week start
date, then select **Generate weekly report**. When the localhost bridge is
running, the report is generated from SQLite-backed local analytics and
persists after refresh.

The same panel lets the owner refresh evidence-backed AI memory and archive a
memory record without deleting it.

## Local-First Limits

- No real analytics APIs are called.
- Reports are only as reliable as their labeled local inputs.
- Mock reports are for demo and development only.
- Small samples remain clearly described as ideas to test, not guarantees.
