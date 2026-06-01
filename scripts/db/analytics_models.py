from __future__ import annotations

ANALYTICS_SOURCES = (
    "manual",
    "mock",
    "platform_api",
    "imported_csv",
    "estimated",
)

PERFORMANCE_TRENDS = (
    "improving",
    "flat",
    "declining",
    "unknown",
)

ANALYTICS_IMPORT_TYPES = (
    "manual_entry",
    "mock_sync",
    "csv_upload",
    "platform_sync",
)

ANALYTICS_IMPORT_STATUSES = (
    "pending",
    "completed",
    "partial",
    "failed",
)

CONTENT_INSIGHT_TYPES = (
    "best_content_type",
    "best_platform",
    "best_hook",
    "best_time",
    "weak_content_type",
    "audience_signal",
    "lead_signal",
    "hashtag_signal",
    "media_signal",
    "safety_signal",
    "recommendation",
)

CONTENT_INSIGHT_STATUSES = (
    "active",
    "dismissed",
    "applied",
    "archived",
)

WEEKLY_REPORT_GENERATORS = (
    "system",
    "ai_mock",
    "ai_provider",
    "manual",
)

AI_MEMORY_TYPES = (
    "brand_rule",
    "content_preference",
    "audience_learning",
    "platform_learning",
    "performance_learning",
    "safety_learning",
    "user_preference",
    "rejected_strategy",
    "approved_strategy",
)

AI_MEMORY_CONFIDENCE_LEVELS = (
    "low",
    "medium",
    "high",
)

AI_MEMORY_STATUSES = (
    "active",
    "archived",
    "superseded",
)
