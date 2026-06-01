# Analytics Foundation

The analytics foundation stores local performance history for approved content. It does not fetch real platform analytics yet.

The local service is implemented in `scripts/services/analytics.py`.

The static web shell now includes an Analytics screen. Until a browser-to-local-service bridge exists, that screen uses a clearly labeled temporary `localStorage` adapter in `apps/web/analytics.js`. The Python service remains the SQLite source of truth for backend behavior and tests.

## Supported Sources

Every snapshot records its provenance:

- `manual`: entered by the user.
- `mock`: clearly fake demo data for development.
- `platform_api`: reserved for future guarded platform integrations.
- `imported_csv`: imported from a user-selected local file.
- `estimated`: explicitly labeled estimate.

Mock and manual metrics must never be presented as live platform analytics.

## Local Tables

- `analytics_snapshots`: point-in-time measurements for a post.
- `post_performance_metrics`: local aggregate totals and trend summaries.
- `analytics_imports`: safe audit records for manual, mock, CSV, or future API imports.
- `content_insights`: explainable observations with evidence and confidence.
- `ai_memory`: durable learning records with evidence and provenance.
- `weekly_reports`: local weekly summaries.

## Simple Rate Formulas

The MVP uses practical comparison formulas:

```text
engagementRate = (likes + comments + shares + saves) / max(reach or impressions or views, 1)
clickThroughRate = clicks / max(impressions or views or reach, 1)
leadRate = leads / max(clicks or impressions or views, 1)
performanceScore =
  engagementRate * 100 * 0.4
  + clickThroughRate * 100 * 0.2
  + leadRate * 100 * 0.3
  + min(saves, 10)
```

The performance score is capped at `100`. These formulas are intentionally simple. They are useful for local comparisons, but they are not universal platform definitions and should not be described as authoritative.

## Analytics Service

`AnalyticsService` supports:

- Creating and updating manual snapshots.
- Filtering snapshots by Brand Brain, platform, date range, and source.
- Generating deterministic fake demo metrics in development/demo mode or after an explicit request.
- Computing and storing per-post performance metrics.
- Computing dashboard totals and platform, content-angle, and content-goal breakdowns.
- Ranking top and underperforming posts.
- Creating simple rule-based content insights.
- Recording analytics import audits.

Snapshots are cumulative point-in-time measurements. When several snapshots exist for one post, summaries use the latest matching snapshot instead of adding every snapshot together. This avoids double-counting a post as its metrics grow over time.

Manual and mock snapshots with the same source, post links, and date are rejected or skipped. Mock generation never overwrites manual data.

## Mock Analytics

Mock generation is local-only and deterministic. It uses existing `published_posts` rows with `publish_mode = mock` or `manual_export`, plus completed local queue rows that do not yet have a matching published-post record.

Every generated row uses:

```text
source = mock
rawMetrics.demo = true
rawMetrics.realPlatformAnalytics = false
```

Mock generation is available by default only when app environment is `development`, `demo`, or `test`. A caller can explicitly request mock generation outside those modes for a deliberate demo workflow.

Run a local summary:

```text
python -m scripts.services.analytics --database data/app.sqlite
```

Generate clearly fake local demo metrics and summarize:

```text
python -m scripts.services.analytics --database data/app.sqlite --generate-mock
```

## AI Learning Safety

Learning records must include evidence and confidence. A low-confidence observation should remain a suggestion to test, not a business claim.

Confidence guidance:

- `low`: fewer than 5 relevant data points.
- `medium`: 5 to 20 relevant data points.
- `high`: more than 20 data points with a consistent pattern.

The app should not delete memory automatically. A user should be able to review, dismiss, archive, or supersede a learning record later.

## Demo Data

The seed script creates one clearly fake `mock` snapshot, one aggregate performance row, one mock import audit, one low-confidence content insight, one low-confidence AI memory record, and one `ai_mock` weekly report.

Initialize and seed a local database:

```text
python -m scripts.db.init_db --database data/app.sqlite
python -m scripts.db.seed_demo --database data/app.sqlite
```

## Not Built Yet

- CSV import parser.
- Browser-to-SQLite API bridge for the Analytics screen.
- AI-provider insight generation.
- Weekly report generator.
- Real platform analytics sync.

Real analytics APIs remain future work behind explicit integration safety gates.
