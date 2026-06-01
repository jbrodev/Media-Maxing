from __future__ import annotations

SCHEDULED_POST_STATUSES = (
    "scheduled",
    "queued",
    "missed",
    "canceled",
    "completed",
    "failed",
    "needs_attention",
)

PUBLISH_QUEUE_STATUSES = (
    "waiting",
    "ready",
    "blocked",
    "processing",
    "mock_published",
    "manually_exported",
    "failed",
    "canceled",
    "skipped",
)

PREFLIGHT_STATUSES = (
    "not_checked",
    "passed",
    "warnings",
    "errors",
    "blocked",
)

PUBLISH_ATTEMPT_TYPES = (
    "preflight",
    "mock_publish",
    "manual_export",
    "future_real_publish",
)

PUBLISH_ATTEMPT_STATUSES = (
    "started",
    "succeeded",
    "failed",
    "skipped",
    "blocked",
)
