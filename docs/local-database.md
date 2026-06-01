# Local Database

The MVP uses a local SQLite database. There is no cloud sync, no authentication database, and no real social API token storage in this foundation.

## Database Choice

The repo does not currently have a package manager, frontend framework, backend framework, or ORM. To avoid overbuilding before the stack is chosen, the first database layer uses:

- SQLite
- SQL migration files
- Python standard library `sqlite3`

This keeps the database local-first and runnable without installing dependencies.

## Files

- `scripts/db/migrations/001_initial_schema.sql`: Initial SQLite schema.
- `scripts/db/init_db.py`: Initializes or migrates the local SQLite database.
- `scripts/db/seed_demo.py`: Adds safe fake demo records for local development.
- `scripts/db/analytics_models.py`: Defines analytics, insight, report, and AI memory constants.
- `scripts/services/analytics.py`: Stores manual and mock analytics, computes local summaries, and creates rule-based insights.
- `scripts/db/engagement_models.py`: Defines engagement, thread, reply suggestion, approval, and import constants.
- `scripts/services/engagement.py`: Creates idempotent fake local inbox records without fetching or replying.
- `scripts/db/brand_profiles.py`: Provides the Brand Brain data model and CRUD service.
- `scripts/db/settings.py`: Loads, validates, and updates local app settings.
- `scripts/db/media_storage.py`: Imports image and video files into local media storage and records metadata in SQLite.
- `tests/test_db_init.py`: Verifies the core tables and safe default settings.
- `tests/test_seed_demo.py`: Verifies demo seed data and idempotency.
- `tests/test_app_settings.py`: Verifies settings defaults, updates, and validation.
- `tests/test_brand_profiles.py`: Verifies Brand Brain create, read, update, list, validation, and seed compatibility.
- `tests/test_media_storage.py`: Verifies media directory creation, local image/video import, metadata persistence, and rejection of unsafe files.
- `tests/test_analytics_service.py`: Verifies manual metrics, mock metrics, latest-snapshot aggregation, summaries, insights, and import audits.
- `tests/test_engagement_service.py`: Verifies safe mock inbox ingestion and duplicate skipping.

## Initialize The Database

From the repo root:

```text
python scripts/db/init_db.py
```

By default this creates:

```text
data/app.sqlite
```

You can also choose a database path:

```text
python scripts/db/init_db.py --database data/app.sqlite
```

The script also honors `DATABASE_URL` when it starts with `file:`.

## Seed Demo Data

From the repo root:

```text
python scripts/db/seed_demo.py
```

The seed script initializes the database if needed, then inserts safe fake demo data for dashboards and UI placeholders.

The demo data includes:

- One local demo user.
- One fake exterior service business Brand Brain.
- Approval-required app settings.
- Five media asset records with placeholder local paths.
- Three content ideas.
- Three generated post drafts.
- Two scheduled posts.
- One manually exported demo published post.
- One mock analytics snapshot.
- One aggregate performance metrics row.
- One mock analytics import audit.
- One low-confidence content insight.
- One low-confidence AI memory row.
- One mock weekly report.
- Approval log records.

Mock engagement inbox records are added separately so the user can deliberately populate the local inbox:

```text
python -m scripts.services.engagement --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care --ingest-mock
```

The script uses stable demo IDs and can be run more than once without creating duplicate demo records.

## Tables

The initial schema creates:

- `users`
- `brand_profiles`
- `app_settings`
- `media_assets`
- `content_ideas`
- `generated_posts`
- `scheduled_posts`
- `published_posts`
- `engagement_items`
- `engagement_threads`
- `reply_suggestions`
- `reply_approvals`
- `engagement_imports`
- `analytics_snapshots`
- `post_performance_metrics`
- `analytics_imports`
- `content_insights`
- `weekly_reports`
- `approval_logs`
- `ai_memory`
- `schema_migrations`

## Safety Defaults

The initializer creates one default `app_settings` row:

```text
automation_level = approval_queue
require_approval_before_publishing = 1
require_approval_before_replying = 1
emergency_pause_enabled = 0
integrations_mode = mock
enable_real_network_calls = 0
enable_real_oauth = 0
enable_real_publishing = 0
token_storage_mode = placeholder_not_stored
```

## App Settings Data Layer

Settings are stored in the local SQLite `app_settings` table.

Safety-critical values use explicit columns:

- `automation_level`
- `require_approval_before_publishing`
- `require_approval_before_replying`
- `emergency_pause_enabled`

Product preferences use `settings_json`:

- `appName`
- `appEnvironment`
- `localDataDirectory`
- `defaultTimezone`
- `defaultPlatformTargets`
- `aiProviderPreference`

The settings layer creates safe defaults if the default row is missing. It validates updates before saving and rejects unsupported automation levels, unsupported platform IDs, unknown fields, empty strings, and non-boolean safety toggles.

Verify locally:

```text
python -m unittest tests.test_app_settings
```

## Brand Brain Data Layer

Brand profiles are stored in the local SQLite `brand_profiles` table.

Core fields use existing columns:

- `businessName` -> `business_name`
- `description` -> `description`
- `brandVoice` -> `voice`
- `services` -> `services_json`
- `serviceAreas` -> `locations_json`
- `targetCustomers` -> `target_audience` and `preferences_json`
- `bannedWords` -> `blocked_phrases_json`

Additional Brand Brain fields use `preferences_json`:

- `tagline`
- `industry`
- `toneRules`
- `preferredWords`
- `commonCTAs`
- `hashtags`
- `website`
- `phone`
- `email`
- `approvalRules`
- `safetyRules`
- `examplePosts`

The service supports creating, reading, updating, and listing brand profiles. It validates `businessName`, rejects unknown fields, keeps array fields as JSON, and validates email shape when an email is provided.

Verify locally:

```text
python -m unittest tests.test_brand_profiles
```

## Local Media Storage

Media files stay on the local machine. The media storage service copies imported images and videos into the configured local app data directory, then writes a `media_assets` row with the original filename, safe internal path, MIME type, file size, media type, timestamps, and editable metadata for future AI generation context.

Default folder layout:

```text
data/
  media/
    originals/
    processed/
    thumbnails/
```

The service creates these folders automatically when a supported file is imported. It accepts common image types (`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`) and video types (`.mp4`, `.mov`, `.webm`, `.m4v`). Unsupported files, empty files, and files over the configured size limit are rejected before copying.

Editable metadata is stored without a migration by using the existing JSON columns:

- `tags_json`: `tags`
- `job_context_json`: `serviceType`, `locationName`, `city`, `state`, `projectDate`, `contentAngle`
- `metadata_json`: `title`, `description`, `qualityRating`, `usageStatus`, `notes`

Supported content angles:

```text
before_after
educational
behind_the_scenes
testimonial
promotion
faq
trust_builder
transformation
seasonal
other
```

Supported usage statuses:

```text
new
reviewed
ready_for_generation
used_in_draft
published
archived
```

Existing media rows still load because missing metadata fields fall back to safe defaults such as the original filename, `other`, and `new`.

Import one file locally:

```text
python scripts/db/media_storage.py path/to/photo.jpg --database data/app.sqlite --local-data-dir data
```

Verify locally:

```text
python -m unittest tests.test_media_storage
```

## Privacy Notes

- Do not commit `data/app.sqlite`.
- Do not store real API keys or raw OAuth tokens in this schema.
- Do not commit real user media.
- Demo media paths are placeholders and do not require actual files yet.
- Real publishing remains disabled.
- Real replies remain disabled.
