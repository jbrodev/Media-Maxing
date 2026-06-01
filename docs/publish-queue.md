# Publish Queue

The Publish Queue is the local readiness area for scheduled posts. It helps the user see what is waiting, ready, blocked, manually exported, or mock-published.

It does not publish to real social platforms, call social APIs, require connected accounts for manual export, or need API keys.

## What The Queue Shows

The web app includes a static Publish Queue screen. When launched through the
localhost bridge, its preflight, mock completion, manual completion, cancel,
and export actions persist through the SQLite services. Opening the HTML file
directly uses localStorage demo records that mirror the SQLite tables:

- `scheduled_posts`
- `publish_queue_items`
- `publish_attempts`

The Python SQLite services and local job runner remain the source of truth for backend behavior and tests.

Backend source of truth:

- Preflight service: `scripts/services/preflight.py`
- Local queue action service: `scripts/services/publish_queue.py`
- Local job runner: `scripts/jobs/local_runner.py`
- Manual export service: `scripts/services/manual_export.py`

## Queue Statuses

Supported local queue statuses:

- `waiting`
- `ready`
- `blocked`
- `processing`
- `mock_published`
- `manually_exported`
- `failed`
- `canceled`
- `skipped`

`ready`, `mock_published`, and `manually_exported` are local states only. They must not be described as real platform publishing.

## Preflight

The screen can run a local preflight check for the selected item. Through the
localhost bridge, it delegates to the backend preflight rules.

The backend source of truth is `scripts/services/preflight.py`, documented in `docs/platform-preflight-matrix.md`.

The current checks include:

- Emergency pause.
- Related scheduled post existence.
- Active scheduled post status.
- Supported platform.
- Caption snapshot.
- Critical safety flags.
- Required media for Instagram, YouTube, and TikTok.
- Linked media existence in the local media library demo.
- Basic headline/title requirement for YouTube and TikTok.
- Connected account readiness for future real publishing.

Blocked items show their preflight errors and warnings in the detail panel. Warning-only items can still be ready for manual export because warnings do not block readiness.

## Account Readiness

Batch 5 adds connected account awareness without enabling real publishing.

The queue now records and displays:

- `accountCheckStatus`
- `matchedSocialAccountId`
- `connectionStatus`
- `missingScopes`
- `requiresReauth`
- `manualExportEligible`
- `mockPublishEligible`
- `realPublishingEligible`

Manual export remains available when content preflight has no blocking errors, even when no social account is connected. A missing account is shown as a warning because future real publishing will require a matching connected account.

Mock connected accounts can satisfy mock/demo account checks. They do not make real publishing available.

Expired, revoked, error, or `requires_reauth` accounts show a reconnect warning and block only future real publishing eligibility. Limited accounts and missing scopes are surfaced as warnings so the user knows what needs attention before real integrations are enabled.

If more than one active account exists for a platform, the system uses a safe local default for now and warns that account selection is needed. A later batch should let the user choose the account explicitly.

Preflight statuses:

- `not_checked`: no local preflight result has been stored yet.
- `passed`: no errors or warnings were found.
- `warnings`: no blocking errors were found, but the user should review warnings.
- `errors`: blocking preflight errors were found.
- `blocked`: emergency pause or another safety state blocks readiness.

Common blocked reasons include emergency pause, unapproved/rejected/revision-requested source drafts, missing caption, missing required media, missing linked media records, unsupported media type, critical safety flags, unsupported platform, and missing title where required.

## Manual Export

Manual export is the safe path before real platform APIs exist.

Creating a manual export package:

- Uses `scripts/services/manual_export.py`.
- Creates a local folder under `data/exports/manual-posts/YYYY-MM-DD/platform-slug-queueItemId/`.
- Writes `caption.txt`, optional `hashtags.txt`, `post.md`, `metadata.json`, `media-manifest.json`, and `posting-instructions.md`.
- Uses the scheduled post caption snapshot, not the mutable draft caption.
- Does not mark the item manually exported automatically.
- Does not call external APIs.

Marking an item manually exported:

- Sets `queueStatus` to `manually_exported`.
- Sets the related scheduled post status to `completed`.
- Creates a local `publish_attempt` with `attemptType = manual_export`.
- Does not call external APIs.

The backend implementation is `PublishQueueService.mark_manually_exported`. It requires warning-only or passed preflight and keeps this as a local audit state only.

Through the localhost bridge, the screen creates the full local folder export
through the Python service. In direct-file fallback mode, it downloads a
browser-side package mirror with caption, hashtags, CTA, media IDs, and
preflight notes. Neither path includes secrets.

See `docs/manual-export.md` for the full package structure and command.

## Mock Publish

Mock publish is demo-only.

It is allowed only when:

- `queueStatus` is `ready`.
- `preflightStatus` is `passed`.
- `mockPublishEnabled` is true.
- Emergency pause is off.

Mock publishing:

- Sets `queueStatus` to `mock_published`.
- Sets the related scheduled post status to `completed`.
- Creates a local `publish_attempt` with `attemptType = mock_publish`.
- Does not call external APIs.
- Does not create a real social post.

The backend implementation is `PublishQueueService.mock_publish`. It requires `queueStatus = ready`, `preflightStatus = passed`, and `mockPublishEnabled = true`. Warning-only preflight is enough for manual export, but not for mock publish.

## Cancel

Canceling a queue item:

- Sets `queueStatus` to `canceled`.
- Sets the related scheduled post status to `canceled` when appropriate.
- Does not delete drafts, media, scheduled posts, or queue records.

## Current Limitations

- Direct-file mode uses a temporary browser adapter; launch through the localhost bridge for SQLite persistence.
- Publish attempts shown through the localhost bridge are local SQLite records.
- Real platform publishing remains disabled by policy.
- Connected social account checks inform readiness, but only future real publishing eligibility is blocked by missing/expired accounts.
