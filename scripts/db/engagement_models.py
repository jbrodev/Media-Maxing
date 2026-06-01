from __future__ import annotations

ENGAGEMENT_ITEM_TYPES = (
    "comment",
    "reply",
    "mention",
    "direct_message",
    "review",
    "lead_message",
    "system_note",
    "unknown",
)

ENGAGEMENT_DIRECTIONS = (
    "inbound",
    "outbound",
    "internal",
)

ENGAGEMENT_SENTIMENTS = (
    "positive",
    "neutral",
    "negative",
    "mixed",
    "unknown",
)

ENGAGEMENT_INTENTS = (
    "praise",
    "question",
    "price_request",
    "booking_request",
    "complaint",
    "spam",
    "partnership",
    "general",
    "urgent",
    "unknown",
)

ENGAGEMENT_PRIORITIES = (
    "low",
    "normal",
    "high",
    "urgent",
)

ENGAGEMENT_STATUSES = (
    "new",
    "needs_reply",
    "reply_suggested",
    "reply_approved",
    "replied_manually",
    "ignored",
    "archived",
    "spam",
    "escalated",
)

ENGAGEMENT_SOURCES = (
    "mock",
    "manual",
    "platform_api",
    "imported_csv",
)

ENGAGEMENT_THREAD_STATUSES = (
    "open",
    "needs_attention",
    "resolved",
    "archived",
    "spam",
)

REPLY_SUGGESTION_STATUSES = (
    "generated",
    "edited",
    "approved",
    "rejected",
    "archived",
)

REPLY_APPROVAL_ACTIONS = (
    "suggest",
    "edit",
    "approve",
    "reject",
    "mark_replied_manually",
    "archive",
    "escalate",
    "mark_spam",
)

REPLY_APPROVAL_ACTOR_TYPES = (
    "user",
    "system",
    "ai",
    "test",
)

ENGAGEMENT_IMPORT_TYPES = (
    "mock_ingestion",
    "manual_entry",
    "csv_upload",
    "platform_sync",
)

ENGAGEMENT_IMPORT_STATUSES = (
    "pending",
    "completed",
    "partial",
    "failed",
)
