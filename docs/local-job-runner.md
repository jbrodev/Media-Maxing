# Local Job Runner

The local job runner is a lightweight Python process that checks scheduled posts and updates publish queue readiness in the local SQLite database.

It does not publish to real social platforms, call social APIs, send replies, scrape data, or require API keys.

## What It Does

The runner performs three MVP jobs:

- `checkDueScheduledPosts`: finds `scheduled_posts` with `status = scheduled` and `scheduled_for <= now`.
- `runPublishQueuePreflight`: checks due `publish_queue_items` in `waiting` or `blocked` states.
- `markMissedScheduledPosts`: marks very old unprocessed scheduled posts as missed.

The runner records local `publish_attempts` with `attempt_type = preflight`. These rows are audit records only. They are not evidence that anything was published externally.

The runner uses the centralized preflight validation service in `scripts/services/preflight.py`, including the platform requirement matrix version stored in each attempt payload.

Full workflow coverage lives in `tests/test_batch4_full_workflow.py`. Runner-specific coverage lives in `tests/test_local_job_runner.py`.

## Commands

Run one local pass:

```powershell
python -m scripts.jobs.local_runner --database data/app.sqlite --once
```

Run repeatedly for local development:

```powershell
python -m scripts.jobs.local_runner --database data/app.sqlite --watch --interval-seconds 30
```

For deterministic verification, pass a fixed clock:

```powershell
python -m scripts.jobs.local_runner --database data/app.sqlite --once --now 2026-06-10T13:00:00Z
```

There is no `npm run jobs:once` command yet because this repository does not currently have a package manager manifest. Use the Python module command above.

## Readiness Behavior

When a due scheduled post passes preflight with no errors:

- `scheduled_posts.status` becomes `queued`.
- `publish_queue_items.queue_status` becomes `ready`.
- `publish_queue_items.preflight_status` becomes `passed` or `warnings`.
- A `publish_attempts` preflight row is created with `attempt_status = succeeded`.

When preflight fails:

- `scheduled_posts.status` becomes `needs_attention`.
- `publish_queue_items.queue_status` becomes `blocked`.
- `publish_queue_items.preflight_status` becomes `errors` or `blocked`.
- Preflight errors and warnings are stored as JSON.
- A `publish_attempts` preflight row is created with `attempt_status = failed` or `blocked`.

Emergency pause uses `preflight_status = blocked` and keeps the item out of the ready queue.

## Preflight Checks

The centralized preflight service checks:

- Emergency pause.
- Scheduled post status.
- Supported platform.
- Caption snapshot.
- Brand profile existence.
- Source draft approval status.
- Critical safety flags.
- Platform-specific media requirements from the matrix.
- Linked media record existence.
- Basic title/headline requirement for YouTube Shorts.
- Connected-account warning for future real publishing.

Missing connected accounts are warnings for manual export. They do not mean real publishing is available.

## Missed Threshold

The default missed threshold is 24 hours.

If a scheduled post is still unprocessed more than 24 hours after `scheduled_for`, the runner marks it `missed` and blocks the related queue item with `missed_threshold_exceeded`.

This is conservative: the app should ask the user what to do rather than silently preparing stale content.

## Locks And Idempotency

The runner uses a small SQLite `local_job_locks` table to avoid overlapping runs. Locks expire after five minutes by default.

Repeated runs are safe enough for the MVP:

- Ready items are not reprocessed by `run_once`.
- Equivalent repeated preflight failures do not create duplicate attempt rows.
- Canceled, completed, and missed scheduled posts are not moved back to ready.

## Local Scheduling Limitation

Local scheduled processing only happens while this app/backend job runner is running. The MVP does not install an operating-system scheduled task, cloud worker, or external cron service.

If the app is closed at the scheduled time, the runner will process due or missed items the next time it is run.

The static web app does not start this runner automatically yet. For now, run it manually with the commands above when testing local scheduling.

## Safety Notes

`ready`, `queued`, `mock_published`, and `manually_exported` are local states. They must not be presented as real publishing.

Real platform publishing remains disabled until a future explicit platform integration adds OAuth, secure token storage, account selection, verified platform API behavior, preflight tests, approval gates, emergency pause enforcement, and user confirmation.
