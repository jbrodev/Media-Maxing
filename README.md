# local-social-ai-manager

A local-first AI social media manager for small businesses, local service businesses, and owner-operators.

This project has a local-first MVP foundation with a static web shell, SQLite
services, and a localhost bridge. It does not publish real posts, send real
replies, or connect real platform APIs by default.

## Project Purpose

The goal is to build a safe local AI command center that helps a business turn its own photos, videos, brand context, and performance history into reviewed social media content.

The app is intended to help non-developer users:

- Define a business identity in a Brand Brain.
- Upload and organize job photos and videos.
- Generate platform-specific post drafts with AI.
- Review, edit, approve, reject, or revise drafts.
- Schedule approved drafts on a local content calendar.
- Prepare a publish queue for manual export first.
- Track analytics manually or with mock/demo data.
- Manage engagement locally with AI-assisted reply suggestions.
- Learn from approvals, rejections, engagement, and performance over time.

## Core Features

Planned core features:

- Brand Brain for business identity, voice, services, offers, claims, and audience context.
- Media Library for local photos, videos, thumbnails, and metadata.
- AI content generation using a mock provider first.
- Drafts and human approval workflow.
- Local-only calendar scheduling.
- Publish Queue for approved and scheduled content.
- Manual export packages for safe posting outside the app.
- Connected Accounts area for future mock and real integration setup.
- Analytics Dashboard for mock, manual, imported, and future platform data.
- Engagement Inbox with local AI reply suggestions.
- AI Memory for learning from user choices and performance.
- Safety Center with emergency pause and kill switch controls.
- Backup, export, and diagnostics tools.

Current completed feature level: local SQLite workflows through Batch 7
recovery, with real publishing and real reply sending intentionally disabled.

## Local-First Privacy Approach

This app is local-first by default. User data should live on the user's machine unless a future feature explicitly requires and documents an external service.

Local-first rules:

- Store app data locally by default.
- Store media files locally by default.
- Use SQLite for MVP data storage.
- Keep real platform integrations disabled until explicitly implemented later.
- Do not scrape social platforms.
- Do not commit local databases, real media, exports, logs, backups, tokens, or secrets.
- Keep mock/demo mode working before adding real providers.
- Keep manual export as the safe publishing path until real publishing is implemented behind strict safety gates.

## Current Tech Stack

The MVP deliberately uses a small dependency-free local stack:

- Frontend: static HTML, CSS, and JavaScript in `apps/web`.
- Local API: Python standard-library localhost-only bridge in `apps/api`.
- Database services: Python and raw SQLite migrations in `scripts`.

Possible later direction from `AGENTS.md`:

- Frontend: Next.js or another web framework only if the static shell becomes too limiting.
- Desktop: Tauri preferred unless the project later chooses Electron.
- Backend/API: keep the current loopback bridge for MVP; adopt a larger framework only when needed.
- Database: SQLite for MVP.
- ORM: Prisma or Drizzle for TypeScript, or SQLAlchemy/SQLModel for Python.
- Media storage: local filesystem under `data/`.
- AI: mock provider by default, with OpenAI, Anthropic, and local providers planned later.
- Jobs: lightweight local job runner first.
- OAuth: server-side only when future integrations are added.
- Token storage: secure local storage/keychain/encryption when available; otherwise `placeholder_not_stored`.

## App Modules

Planned app modules:

- Home
- Onboarding
- Brand Brain
- Media Library
- Generate
- Drafts
- Calendar
- Publish Queue
- Manual Export
- Connected Accounts
- Social Integration Setup
- Analytics
- Engagement Inbox
- Weekly Reports
- AI Memory
- Settings
- Safety Center
- Backup & Data
- Diagnostics

Current folders:

```text
apps/
  web/
  desktop/
  api/
packages/
  shared/
  ui/
  types/
  config/
docs/
scripts/
data/
  media/
  exports/
  logs/
```

## Setup Instructions

The web app is currently a static HTML/CSS/JavaScript app. No frontend framework or package manager has been installed yet.

For now:

1. Review `AGENTS.md` before making changes.
2. Copy `.env.example` to `.env` when local server-side configuration is needed.
3. Do not add real secrets to committed files.
4. Follow the batch prompts in order.
5. Run `python -m apps.api.local_server --database data/app.sqlite --port 8000`.
6. Open `http://127.0.0.1:8000` for the SQLite-backed web shell.

The localhost server automatically loads a repo-root `.env` file when it
exists. Use `--env-file PATH` only when a different local file is needed.

Opening `apps/web/index.html` directly remains available as a browser-only demo
fallback. See `docs/local-api-bridge.md`.

Python services provide the local SQLite database, scheduling, preflight, job runner, and manual export behavior.

## Development Commands

No package manager commands exist yet because there is no `package.json`, `pyproject.toml`, `Makefile`, or equivalent tooling file.

Current direct commands:

```text
python -m scripts.db.init_db --database data/app.sqlite
python -m scripts.db.seed_demo --database data/app.sqlite
python -m apps.api.local_server --database data/app.sqlite --port 8000
python -m scripts.jobs.local_runner --database data/app.sqlite --once
python -m scripts.jobs.local_runner --database data/app.sqlite --watch --interval-seconds 30
python -m scripts.services.manual_export --database data/app.sqlite --queue-item-id QUEUE_ITEM_ID
python -m scripts.services.analytics --database data/app.sqlite
python -m scripts.services.analytics --database data/app.sqlite --generate-mock
python -m scripts.services.engagement --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care --ingest-mock
python -m scripts.services.ai_memory --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care
python -m scripts.services.weekly_reports --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care --week-start-date 2026-06-08
python -m unittest tests.test_integration_flags
python -m unittest tests.test_platform_http_client
python -m unittest tests.test_integration_setup_service
python -m unittest discover tests
python -m compileall -q scripts tests
node --check apps/web/settings.js
node --check apps/web/generate.js
```

Planned command names may include:

```text
npm run dev
npm run build
npm run lint
npm run typecheck
npm run test
npm run db:migrate
npm run db:seed
npm run jobs:once
npm run jobs:dev
npm run launch:check
npm run desktop:dev
npm run desktop:build
```

These commands are examples only until the project tooling is created.

## Environment Variables

Use `.env.example` as the committed template. Do not commit `.env`.

Current environment template includes:

```text
APP_ENV=development
LOCAL_DATA_DIR=./data
DATABASE_URL=file:./data/app.sqlite

OPENAI_API_KEY=
ANTHROPIC_API_KEY=

INTEGRATIONS_MODE=mock
ENABLE_REAL_NETWORK_CALLS=false
ENABLE_REAL_OAUTH=false
ENABLE_REAL_PUBLISHING=false
ALLOW_NETWORK_IN_TESTS=false
TOKEN_STORAGE_MODE=placeholder_not_stored

META_CLIENT_ID=
META_CLIENT_SECRET=
META_REDIRECT_URI=
META_GRAPH_API_VERSION=
META_ENABLE_REAL_OAUTH=false
META_ENABLE_REAL_PUBLISHING=false

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GOOGLE_ENABLE_REAL_OAUTH=false
GOOGLE_ENABLE_REAL_PUBLISHING=false

TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_REDIRECT_URI=
TIKTOK_ENABLE_REAL_OAUTH=false
TIKTOK_ENABLE_REAL_PUBLISHING=false

LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=
LINKEDIN_ENABLE_REAL_OAUTH=false
LINKEDIN_ENABLE_REAL_PUBLISHING=false

X_CLIENT_ID=
X_CLIENT_SECRET=
X_REDIRECT_URI=
X_ENABLE_REAL_OAUTH=false
X_ENABLE_REAL_PUBLISHING=false
```

Real provider keys and platform credentials are optional future configuration values. They must never be committed.

## Safety Rules

Non-negotiable safety rules:

- No real publishing yet.
- No real comment replies or DMs yet.
- No auto-replies.
- No scraping.
- No secrets committed.
- Mock/demo mode first.
- Human approval required before publishing or replying.
- Generated posts must default to review, not automatic approval.
- Scheduling must only allow approved and safe drafts.
- Emergency pause must block scheduling, queue readiness, mock publishing, future real publishing, future real replies, and unsafe automation.
- AI must not invent testimonials, customer names, pricing, availability, certifications, insurance, awards, guarantees, or fake social proof.
- Real platform APIs must come later behind explicit safety gates.

See `docs/safety-and-automation-policy.md` and `AGENTS.md` for the full policy.

## Current Project Status

Current status:

- Repository folder structure exists.
- Placeholder README files exist in empty app, package, script, and local-data folders.
- Starter docs exist for roadmap, safety policy, and database schema planning.
- `.env.example` exists.
- `.gitignore` protects secrets, local databases, local media, exports, logs, build output, dependencies, Python virtual environments, and desktop build artifacts.
- Shared TypeScript product types exist.
- Local SQLite initialization exists.
- Local app settings data layer exists.
- Brand Brain data model and CRUD service exist.
- Local media storage service exists for image/video imports and SQLite metadata.
- Media Library screen supports demo media browsing, filtering, local-only import metadata, and manual metadata editing.
- Safe fake demo seed data exists for dashboards and UI placeholders.
- AI provider abstraction, mock provider, prompt registry, content generation service, Generate screen, draft persistence, Drafts screen, approval workflow, approval queue service, and prompt evaluation fixtures exist.
- Local scheduling models and service exist.
- Calendar screen exists in the static web shell.
- Approved drafts can be scheduled locally through the SQLite-backed browser shell.
- Local job runner exists for due scheduled posts and preflight.
- Publish Queue screen exists in the static web shell.
- Platform requirement matrix and preflight validation service exist.
- Manual export package service exists.
- Local Publish Queue action service exists for marking manually exported and mock-publish transitions.
- Social connector registry, mock OAuth scaffolding, Connected Accounts UI, token safety helpers, Meta connector scaffolds, account-aware preflight, and Social Integration Setup helper exist.
- Integration feature flag validation and a safe server-only platform HTTP client foundation exist for future OAuth/provider work.
- Guarded Meta OAuth token exchange readiness exists behind explicit safety flags and mocked-test coverage; mock mode remains default and real publishing remains disabled.
- Meta account discovery and connector health checks now exist as safe scaffolding with mocked-test coverage; real API discovery is not called by default.
- YouTube connector scaffolding now supports mock OAuth/channel health readiness; video upload and publishing remain disabled.
- TikTok connector scaffolding now supports mock OAuth/profile health readiness; video posting remains disabled.
- LinkedIn connector scaffolding now supports mock OAuth/profile health readiness; text, image, and video publishing remain disabled.
- X connector scaffolding now supports mock OAuth/profile health readiness; text, image, and video publishing remain disabled.
- Batch 7 analytics storage foundation now exists for snapshots, aggregate performance metrics, import audits, explainable content insights, AI memory, and weekly reports.
- Safe fake demo analytics are labeled `mock`; the demo weekly report is labeled `ai_mock`.
- Local analytics service now supports manual snapshots, deterministic mock metrics, latest-snapshot summaries, breakdowns, rankings, import audits, and rule-based insights.
- Analytics Dashboard screen now supports SQLite-backed local summaries, filters, breakdowns, rankings, insight review actions, manual snapshots, and clearly labeled mock metric generation.
- Engagement Inbox database foundation now supports local threads, triage fields, reply-suggestion records, approval audits, import audits, and idempotent fake inbox ingestion. Real comment fetching and reply sending remain disabled.
- Local AI reply suggestions now use Brand Brain context, versioned prompt provenance, deterministic mock generation, local safety review, persisted history, and audit rows. Suggestions remain review-only and are never sent externally.
- Local reply approval workflow now supports editing, local approval, rejection, manual-reply tracking, escalation, spam marking, archive actions, critical-flag blocking, and audit history. Approval never sends a platform reply.
- Engagement Inbox browser screen persists the local reply workflow through the localhost SQLite bridge and keeps a direct-file `localStorage` fallback for static inspection.
- Local AI memory service now promotes explainable analytics insights and local draft/reply review decisions into idempotent evidence-backed memory without storing private engagement text.
- Local weekly report service now upserts one deterministic report per brand and week, preserving mock/manual provenance and labeling mock-only reports as `ai_mock`.

Batch 4 docs:

- `docs/scheduling.md`
- `docs/publish-queue.md`
- `docs/local-job-runner.md`
- `docs/manual-export.md`
- `docs/platform-preflight-matrix.md`

Batch 5 setup docs:

- `docs/social-connectors.md`
- `docs/oauth-flow.md`
- `docs/token-security.md`
- `docs/meta-integration.md`
- `docs/connected-accounts.md`
- `docs/social-integration-setup.md`

Batch 6 integration safety docs:

- `docs/integration-feature-flags.md`
- `docs/platform-http-client.md`
- `docs/meta-oauth-real-mode.md`
- `docs/connector-health-checks.md`
- `docs/youtube-integration.md`
- `docs/tiktok-integration.md`
- `docs/linkedin-integration.md`
- `docs/x-integration.md`
- `docs/integration-security-review.md`

Batch 7 local learning and inbox docs:

- `docs/analytics.md`
- `docs/engagement-inbox.md`
- `docs/reply-suggestions.md`
- `docs/reply-approval-workflow.md`
- `docs/ai-learning-loop.md`
- `docs/weekly-reports.md`

Not built yet:

- Desktop app.
- Production media upload UI wired to local storage.
- AI media analysis and auto-tagging.
- Real social integrations and real OAuth token exchange.
- Trusted desktop file-picker bridge for production media import.
- Safety Center.
- Backup and diagnostics.
- Package-manager based lint/typecheck/build commands.
