# Local Scheduling

This app schedules content locally only. Scheduling creates calendar records and publish queue records in SQLite, but it does not publish to any social platform, call social APIs, or create operating-system scheduled tasks.

## What Scheduling Does

The scheduling service takes an already approved generated draft and creates:

- A `scheduled_posts` row for the local calendar.
- A `publish_queue_items` row with `queue_status = waiting`.
- An `approval_logs` row for the scheduling action.
- A lightweight readiness update on the source `generated_posts` row.

The queue item `due_at` value is the same time as the scheduled post `scheduled_for` value. A later local job runner can use that due time to decide when to run preflight/readiness checks.

Backend source of truth:

- Scheduling service: `scripts/services/scheduling.py`
- Approval gate: `scripts/services/approval_queue.py`
- Queue readiness runner: `scripts/jobs/local_runner.py`
- Full Batch 4 workflow test: `tests/test_batch4_full_workflow.py`

## Eligibility Rules

A draft can be scheduled only when the approval queue service says it is eligible. The current checks require:

- The draft approval status is `approved`.
- Emergency pause is disabled.
- The platform is supported.
- The caption/content is present.
- Critical safety flags are absent.
- The related Brand Brain exists.
- Linked media assets exist.
- Media-required platforms such as Instagram, YouTube, and TikTok have linked media.
- The scheduled time is a valid future datetime, except explicit development test items.

Rejected, archived, revision-requested, or needs-review drafts cannot be scheduled.

## Snapshot Behavior

Scheduling copies the current draft content into the scheduled post:

- Caption snapshot.
- Media asset IDs.
- Platform.
- Hashtags.
- CTA.
- Hook/headline.
- Alt text.
- Safety flags.

This prevents later draft edits from silently changing already scheduled content. If a scheduled post needs new content, the user should explicitly reschedule or update the scheduled item in a future UI flow.

## Timezones

The service stores `scheduled_for` and queue `due_at` as UTC ISO timestamps. It also stores the source timezone on both `scheduled_posts` and `publish_queue_items` for display and local interpretation.

If no timezone is supplied, the service uses the app default timezone from local settings.

The current implementation uses Python native `datetime` and `zoneinfo`. Ambiguous daylight-saving local times are not deeply modeled yet; future calendar UI work should make timezone selection explicit when needed.

## Cancel And Reschedule

Canceling a scheduled post:

- Sets the scheduled post status to `canceled`.
- Sets the related queue item to `canceled` when it has not already been processed.
- Creates an approval log entry.

Rescheduling:

- Updates `scheduled_for` on the scheduled post.
- Updates `due_at` on the queue item when the queue item is still `waiting` or `blocked`.
- Refuses to modify processed queue states.
- Is blocked by emergency pause.

## Safety Notes

Scheduling remains local-only. `waiting`, `queued`, `completed`, or similar local statuses are not proof that anything was published. Real publishing remains disabled until a future platform-specific task adds OAuth, secure token storage, preflight tests, approval gates, emergency pause enforcement, and explicit user confirmation.

## Current Web Calendar Screen

The static web app includes a first Calendar screen with Week, Month, and List views. Until an API bridge exists, it uses a temporary browser adapter backed by localStorage and mirrors the local scheduling service behavior for demo records.

The screen can:

- Show local scheduled post cards with platform, time, status, caption preview, media count, safety flag count, business name, and queue status.
- Filter by platform and scheduled post status.
- Open a detail panel with schedule metadata, caption snapshot, linked media IDs, draft ID, queue status, preflight status, notes, and timestamps.
- Reschedule waiting or blocked queue items in the browser demo.
- Cancel unprocessed scheduled posts in the browser demo.
- Mark a scheduled item as needing attention.
- Copy the caption for manual posting.

The screen does not publish anything, does not call real social APIs, and does not create operating-system scheduled tasks. The "Schedule approved drafts" button points users back to Drafts until the full approved-draft-to-calendar workflow is built.

## Publish Queue Screen

The static web app now includes a Publish Queue screen for local queue readiness. It shows waiting, ready, blocked, failed, mock-published, and manually-exported items from the temporary browser adapter.

The screen can run local preflight, mark an item manually exported, record a mock publish when mock publishing is enabled and preflight has passed, cancel a queue item, copy captions, and download a simple manual export instruction file.

These actions update local demo records only. They do not call social APIs and do not create real social posts.

## Scheduling From Drafts

The Drafts screen now includes a local Schedule action for approved drafts. The static browser implementation mirrors the Python scheduling service until the API bridge is available.

Scheduling from Drafts:

- Is shown only for drafts with `approvalStatus = approved`.
- Rechecks scheduling eligibility before opening and again before saving.
- Blocks needs-review, rejected, revision-requested, and archived drafts.
- Blocks critical safety flags such as fake testimonials, unsupported guarantees, approval bypass attempts, private customer information risk, and unsupported claims.
- Blocks scheduling while emergency pause is enabled.
- Requires a date, time, and timezone.
- Requires future date/time unless the app is in development mode and the user explicitly confirms a past test item.
- Snapshots caption, hashtags, CTA, hook/headline, alt text, safety flags, platform, and media IDs.
- Creates a local `scheduled_posts` browser record.
- Creates a local `publish_queue_items` browser record with `queueStatus = waiting`.
- Creates a local approval/audit log entry.

Duplicate protection checks for an existing non-canceled schedule for the same draft at the same scheduled time and also disables the confirm button while scheduling is in progress.

This is still local-only. It does not publish, does not call social APIs, and does not mutate the source draft content.

## Full Local Workflow

The intended Batch 4 flow is:

1. Generate or seed a draft.
2. Approve the draft in the local approval workflow.
3. Schedule the approved draft through `CalendarSchedulingService` or the Drafts screen demo adapter.
4. Confirm a `scheduled_posts` row and `publish_queue_items` row exist.
5. Run the local job runner when the scheduled time is due.
6. Review queue readiness and preflight warnings/errors.
7. Export a manual posting package if preflight passes or has warnings only.
8. After the user manually posts or finishes exporting, mark the queue item manually exported.

The integration test covers this path without social APIs, real credentials, or real publishing.
