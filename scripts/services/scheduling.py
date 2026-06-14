from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from scripts.ai.platform_limits import caption_limit_for, trim_to_limit
from scripts.db.drafts import SavedGeneratedDraft, get_generated_draft
from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.scheduling_models import SCHEDULED_POST_STATUSES
from scripts.db.settings import load_app_settings
from scripts.services.approval_queue import ApprovalQueueService


EDITABLE_QUEUE_STATUSES = {"waiting", "blocked"}
CANCELABLE_QUEUE_STATUSES = {"waiting", "ready", "blocked", "failed"}


class CalendarSchedulingError(ValueError):
    def __init__(self, message: str, error_codes: list[str] | None = None):
        super().__init__(message)
        self.error_codes = error_codes or []


@dataclass(frozen=True)
class PublishQueueItem:
    id: str
    scheduledPostId: str
    generatedPostId: str
    brandProfileId: str
    platform: str
    queueStatus: str
    dueAt: str
    timezone: str
    priority: int
    preflightStatus: str
    preflightErrors: list[str] = field(default_factory=list)
    preflightWarnings: list[str] = field(default_factory=list)
    mockPublishEnabled: bool = False
    manualExportRequired: bool = True
    lastCheckedAt: str | None = None
    createdAt: str = ""
    updatedAt: str = ""


@dataclass(frozen=True)
class ScheduledPost:
    id: str
    generatedPostId: str
    brandProfileId: str
    platform: str
    scheduledFor: str
    timezone: str
    status: str
    captionSnapshot: str
    mediaAssetIds: list[str]
    platformAccountId: str | None
    publishQueueItemId: str | None
    recurrenceRule: str | None
    isRecurringTemplate: bool
    userNotes: str | None
    preflightSnapshot: dict[str, Any]
    scheduleMetadata: dict[str, Any]
    createdAt: str
    updatedAt: str
    canceledAt: str | None


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _validate_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise CalendarSchedulingError(
            f"Unsupported timezone {timezone_name!r}.",
            ["invalid_timezone"],
        ) from error


def _parse_scheduled_for(raw_value: str, timezone_name: str) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise CalendarSchedulingError(
            "scheduled_for is required.",
            ["invalid_scheduled_for"],
        )
    normalized = raw_value.strip()
    parse_input = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    try:
        parsed = datetime.fromisoformat(parse_input)
    except ValueError as error:
        raise CalendarSchedulingError(
            "scheduled_for must be a valid ISO datetime.",
            ["invalid_scheduled_for"],
        ) from error

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_validate_timezone(timezone_name))
    return _utc_iso(parsed)


def _row_to_scheduled_post(row: sqlite3.Row) -> ScheduledPost:
    return ScheduledPost(
        id=row["id"],
        generatedPostId=row["generated_post_id"],
        brandProfileId=row["brand_profile_id"],
        platform=row["platform"],
        scheduledFor=row["scheduled_for"],
        timezone=row["timezone"],
        status=row["status"],
        captionSnapshot=row["caption_snapshot"],
        mediaAssetIds=_decode_json(
            row["media_asset_ids_json"] or row["media_snapshot_json"], []
        ),
        platformAccountId=row["platform_account_id"],
        publishQueueItemId=row["publish_queue_item_id"],
        recurrenceRule=row["recurrence_rule"],
        isRecurringTemplate=bool(row["is_recurring_template"]),
        userNotes=row["user_notes"],
        preflightSnapshot=_decode_json(row["preflight_snapshot_json"], {}),
        scheduleMetadata=_decode_json(row["schedule_metadata_json"], {}),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
        canceledAt=row["canceled_at"],
    )


def _row_to_queue_item(row: sqlite3.Row) -> PublishQueueItem:
    return PublishQueueItem(
        id=row["id"],
        scheduledPostId=row["scheduled_post_id"],
        generatedPostId=row["generated_post_id"],
        brandProfileId=row["brand_profile_id"],
        platform=row["platform"],
        queueStatus=row["queue_status"],
        dueAt=row["due_at"],
        timezone=row["timezone"],
        priority=int(row["priority"]),
        preflightStatus=row["preflight_status"],
        preflightErrors=_decode_json(row["preflight_errors_json"], []),
        preflightWarnings=_decode_json(row["preflight_warnings_json"], []),
        mockPublishEnabled=bool(row["mock_publish_enabled"]),
        manualExportRequired=bool(row["manual_export_required"]),
        lastCheckedAt=row["last_checked_at"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


class CalendarSchedulingService:
    """Local-only calendar scheduling service.

    This service creates scheduled posts and publish queue items. It does
    not publish, call social APIs, or create operating-system jobs.
    """

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))
        self.approval_queue = ApprovalQueueService(self.database_path)

    def list_scheduled_posts(self, *, start: str, end: str) -> list[ScheduledPost]:
        start_utc = _parse_scheduled_for(start, self._default_timezone())
        end_utc = _parse_scheduled_for(end, self._default_timezone())
        if start_utc > end_utc:
            raise CalendarSchedulingError(
                "start must be before end.",
                ["invalid_date_range"],
            )
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM scheduled_posts
                WHERE scheduled_for >= ?
                  AND scheduled_for < ?
                ORDER BY scheduled_for ASC, created_at ASC
                """,
                (start_utc, end_utc),
            ).fetchall()
        return [_row_to_scheduled_post(row) for row in rows]

    def get_scheduled_post(self, scheduled_post_id: str) -> ScheduledPost | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM scheduled_posts WHERE id = ?",
                (scheduled_post_id,),
            ).fetchone()
        return _row_to_scheduled_post(row) if row else None

    def get_publish_queue_item(self, queue_item_id: str | None) -> PublishQueueItem:
        if not queue_item_id:
            raise CalendarSchedulingError(
                "publish_queue_item_id is required.",
                ["missing_publish_queue_item"],
            )
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM publish_queue_items WHERE id = ?",
                (queue_item_id,),
            ).fetchone()
        if row is None:
            raise CalendarSchedulingError(
                f"Publish queue item {queue_item_id!r} does not exist.",
                ["missing_publish_queue_item"],
            )
        return _row_to_queue_item(row)

    def schedule_approved_draft(
        self,
        draft_id: str,
        *,
        scheduled_for: str,
        timezone: str | None = None,
        timezone_name: str | None = None,
        user_notes: str | None = None,
        actor_label: str = "local_user",
        allow_past_test_item: bool = False,
    ) -> ScheduledPost:
        draft = self._require_draft(draft_id)
        scheduling = self.approval_queue.check_scheduling_eligibility(draft_id)
        if not scheduling.eligible:
            raise CalendarSchedulingError(
                "Draft is not eligible for scheduling.",
                scheduling.error_codes,
            )

        if timezone and timezone_name and timezone != timezone_name:
            raise CalendarSchedulingError(
                "Use either timezone or timezone_name, not both.",
                ["conflicting_timezone_values"],
            )
        timezone_value = timezone or timezone_name or self._default_timezone()
        scheduled_for_utc = _parse_scheduled_for(scheduled_for, timezone_value)
        self._ensure_future_datetime(
            scheduled_for_utc,
            allow_past_test_item=allow_past_test_item,
        )

        scheduled_id = str(uuid.uuid4())
        queue_id = str(uuid.uuid4())
        now = _now_utc()
        media_ids = list(draft.mediaAssetIds)
        preflight_snapshot = {
            "eligible": True,
            "errors": [],
            "warnings": scheduling.warnings,
            "source": "approval_queue",
            "realPublishing": False,
        }
        schedule_metadata = {
            "hashtags": list(draft.hashtags),
            "callToAction": draft.callToAction,
            "headline": draft.headline,
            "hook": draft.hook,
            "altText": draft.altText,
            "safetyFlags": list(draft.safetyFlags),
            "snapshotSource": "generated_posts",
        }

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            try:
                connection.execute("BEGIN")
                connection.execute(
                    """
                    INSERT INTO scheduled_posts (
                      id, generated_post_id, brand_profile_id, platform,
                      scheduled_for, timezone, status, caption_snapshot,
                      media_asset_ids_json, media_snapshot_json,
                      publish_queue_item_id, user_notes, preflight_snapshot_json,
                      schedule_metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scheduled_id,
                        draft.id,
                        draft.brandProfileId,
                        draft.platform,
                        scheduled_for_utc,
                        timezone_value,
                        "scheduled",
                        draft.caption,
                        _json(media_ids),
                        _json(media_ids),
                        queue_id,
                        _clean_optional_text(user_notes),
                        _json(preflight_snapshot),
                        _json(schedule_metadata),
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO publish_queue_items (
                      id, scheduled_post_id, generated_post_id, brand_profile_id,
                      platform, queue_status, due_at, timezone, priority,
                      preflight_status, preflight_errors_json,
                      preflight_warnings_json, mock_publish_enabled,
                      manual_export_required, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        queue_id,
                        scheduled_id,
                        draft.id,
                        draft.brandProfileId,
                        draft.platform,
                        "waiting",
                        scheduled_for_utc,
                        timezone_value,
                        100,
                        "not_checked",
                        _json([]),
                        _json(scheduling.warnings),
                        0,
                        1,
                        now,
                        now,
                    ),
                )
                self._append_log(
                    connection,
                    entity_id=scheduled_id,
                    action="scheduled",
                    actor_label=actor_label,
                    notes="Draft scheduled locally. No publishing was performed.",
                    changed_fields={
                        "generatedPostId": draft.id,
                        "publishQueueItemId": queue_id,
                        "scheduledFor": scheduled_for_utc,
                        "timezone": timezone_value,
                        "status": "scheduled",
                    },
                    created_at=now,
                )
                self._update_generated_post_readiness(
                    connection,
                    draft.id,
                    scheduled_for_utc,
                    "waiting",
                    now,
                )
                connection.commit()
            except sqlite3.Error as error:
                connection.rollback()
                raise CalendarSchedulingError(str(error), ["database_error"]) from error

        return self._require_scheduled_post(scheduled_id)

    def update_scheduled_time(
        self,
        scheduled_post_id: str,
        *,
        scheduled_for: str,
        timezone: str | None = None,
        actor_label: str = "local_user",
        allow_past_test_item: bool = False,
    ) -> ScheduledPost:
        current = self._require_scheduled_post(scheduled_post_id)
        if load_app_settings(self.database_path).emergencyPauseEnabled:
            raise CalendarSchedulingError(
                "Emergency pause blocks rescheduling active local posts.",
                ["emergency_pause_enabled"],
            )
        timezone_value = timezone or current.timezone or self._default_timezone()
        scheduled_for_utc = _parse_scheduled_for(scheduled_for, timezone_value)
        self._ensure_future_datetime(
            scheduled_for_utc,
            allow_past_test_item=allow_past_test_item,
        )
        queue = self._queue_for_scheduled_post(current.id)
        if queue and queue.queueStatus not in EDITABLE_QUEUE_STATUSES:
            raise CalendarSchedulingError(
                "Only waiting or blocked queue items can be rescheduled.",
                ["queue_status_not_editable"],
            )

        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                UPDATE scheduled_posts
                SET scheduled_for = ?,
                    timezone = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (scheduled_for_utc, timezone_value, now, current.id),
            )
            if queue:
                connection.execute(
                    """
                    UPDATE publish_queue_items
                    SET due_at = ?,
                        timezone = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (scheduled_for_utc, timezone_value, now, queue.id),
                )
            self._append_log(
                connection,
                entity_id=current.id,
                action="rescheduled",
                actor_label=actor_label,
                notes="Scheduled post date/time updated locally.",
                changed_fields={
                    "previousScheduledFor": current.scheduledFor,
                    "scheduledFor": scheduled_for_utc,
                    "timezone": timezone_value,
                },
                created_at=now,
            )
            self._update_generated_post_readiness(
                connection,
                current.generatedPostId,
                scheduled_for_utc,
                "waiting",
                now,
            )
            connection.commit()
        return self._require_scheduled_post(current.id)

    def update_scheduled_notes(
        self,
        scheduled_post_id: str,
        user_notes: str | None,
        *,
        actor_label: str = "local_user",
    ) -> ScheduledPost:
        current = self._require_scheduled_post(scheduled_post_id)
        now = _now_utc()
        cleaned_notes = _clean_optional_text(user_notes)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                UPDATE scheduled_posts
                SET user_notes = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (cleaned_notes, now, current.id),
            )
            self._append_log(
                connection,
                entity_id=current.id,
                action="notes_updated",
                actor_label=actor_label,
                notes="Scheduled post notes updated locally.",
                changed_fields={"userNotes": cleaned_notes},
                created_at=now,
            )
            connection.commit()
        return self._require_scheduled_post(current.id)

    def trim_caption_to_limit(
        self,
        scheduled_post_id: str,
        *,
        actor_label: str = "local_user",
    ) -> ScheduledPost:
        """Trim a scheduled post's caption so it fits the platform limit.

        Local-only auto-fix for the preflight ``caption_too_long`` error. Trims
        the scheduled caption snapshot (and the source draft's caption) to the
        platform's max length on a word boundary. No-op when already within
        the limit. Never publishes.
        """
        current = self._require_scheduled_post(scheduled_post_id)
        limit = caption_limit_for(current.platform)
        caption = current.captionSnapshot or ""
        if len(caption) <= limit:
            return current
        trimmed = trim_to_limit(caption, limit)
        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                UPDATE scheduled_posts
                SET caption_snapshot = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (trimmed, now, current.id),
            )
            connection.execute(
                """
                UPDATE generated_posts
                SET caption = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (trimmed, now, current.generatedPostId),
            )
            self._append_log(
                connection,
                entity_id=current.id,
                action="caption_trimmed_to_limit",
                actor_label=actor_label,
                notes=(
                    f"Caption trimmed from {len(caption)} to {len(trimmed)} "
                    f"characters to fit the {current.platform} limit of {limit}."
                ),
                changed_fields={
                    "previousCaptionLength": len(caption),
                    "captionLength": len(trimmed),
                    "platform": current.platform,
                    "maxCaptionLength": limit,
                },
                created_at=now,
            )
            connection.commit()
        return self._require_scheduled_post(current.id)

    def cancel_scheduled_post(
        self,
        scheduled_post_id: str,
        *,
        actor_label: str = "local_user",
        reason: str | None = None,
    ) -> ScheduledPost:
        current = self._require_scheduled_post(scheduled_post_id)
        queue = self._queue_for_scheduled_post(current.id)
        if queue and queue.queueStatus not in CANCELABLE_QUEUE_STATUSES and queue.queueStatus != "canceled":
            raise CalendarSchedulingError(
                "Processed queue items cannot be canceled by this scheduling action.",
                ["queue_status_already_processed"],
            )

        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                UPDATE scheduled_posts
                SET status = 'canceled',
                    canceled_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, now, current.id),
            )
            if queue and queue.queueStatus != "canceled":
                connection.execute(
                    """
                    UPDATE publish_queue_items
                    SET queue_status = 'canceled',
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (now, queue.id),
                )
            self._append_log(
                connection,
                entity_id=current.id,
                action="canceled",
                actor_label=actor_label,
                notes=reason or "Scheduled post canceled locally.",
                changed_fields={
                    "previousStatus": current.status,
                    "status": "canceled",
                    "publishQueueItemId": queue.id if queue else None,
                },
                created_at=now,
            )
            self._update_generated_post_readiness(
                connection,
                current.generatedPostId,
                current.scheduledFor,
                "canceled",
                now,
            )
            connection.commit()
        return self._require_scheduled_post(current.id)

    def mark_queued(self, scheduled_post_id: str, *, actor_label: str = "system") -> ScheduledPost:
        return self._set_scheduled_status(
            scheduled_post_id,
            "queued",
            action="marked_queued",
            actor_label=actor_label,
        )

    def mark_completed(self, scheduled_post_id: str, *, actor_label: str = "system") -> ScheduledPost:
        return self._set_scheduled_status(
            scheduled_post_id,
            "completed",
            action="marked_completed",
            actor_label=actor_label,
        )

    def mark_missed(self, scheduled_post_id: str, *, actor_label: str = "system") -> ScheduledPost:
        return self._set_scheduled_status(
            scheduled_post_id,
            "missed",
            action="marked_missed",
            actor_label=actor_label,
        )

    def mark_needs_attention(
        self,
        scheduled_post_id: str,
        *,
        actor_label: str = "local_user",
    ) -> ScheduledPost:
        current = self._require_scheduled_post(scheduled_post_id)
        queue = self._queue_for_scheduled_post(current.id)
        if queue and queue.queueStatus not in EDITABLE_QUEUE_STATUSES:
            raise CalendarSchedulingError(
                "Only waiting or blocked queue items can be marked needs attention.",
                ["queue_status_not_editable"],
            )

        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                UPDATE scheduled_posts
                SET status = 'needs_attention',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, current.id),
            )
            if queue:
                errors = list(queue.preflightErrors)
                if "needs_attention" not in errors:
                    errors.append("needs_attention")
                connection.execute(
                    """
                    UPDATE publish_queue_items
                    SET queue_status = 'blocked',
                        preflight_status = 'blocked',
                        preflight_errors_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (_json(errors), now, queue.id),
                )
            self._append_log(
                connection,
                entity_id=current.id,
                action="marked_needs_attention",
                actor_label=actor_label,
                notes="Scheduled post marked needs attention locally.",
                changed_fields={
                    "previousStatus": current.status,
                    "status": "needs_attention",
                    "publishQueueItemId": queue.id if queue else None,
                },
                created_at=now,
            )
            self._update_generated_post_readiness(
                connection,
                current.generatedPostId,
                current.scheduledFor,
                "blocked",
                now,
            )
            connection.commit()
        return self._require_scheduled_post(current.id)

    def _set_scheduled_status(
        self,
        scheduled_post_id: str,
        status: str,
        *,
        action: str,
        actor_label: str,
    ) -> ScheduledPost:
        if status not in SCHEDULED_POST_STATUSES:
            raise CalendarSchedulingError(
                f"Unsupported scheduled post status {status!r}.",
                ["invalid_scheduled_status"],
            )
        current = self._require_scheduled_post(scheduled_post_id)
        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(
                """
                UPDATE scheduled_posts
                SET status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (status, now, current.id),
            )
            self._append_log(
                connection,
                entity_id=current.id,
                action=action,
                actor_label=actor_label,
                notes=f"Scheduled post marked {status} locally.",
                changed_fields={"previousStatus": current.status, "status": status},
                created_at=now,
            )
            connection.commit()
        return self._require_scheduled_post(current.id)

    def _default_timezone(self) -> str:
        return load_app_settings(self.database_path).defaultTimezone

    def _ensure_future_datetime(
        self,
        scheduled_for_utc: str,
        *,
        allow_past_test_item: bool,
    ) -> None:
        parsed = datetime.fromisoformat(
            scheduled_for_utc.removesuffix("Z") + "+00:00"
        )
        if parsed <= datetime.now(timezone.utc) and not (
            allow_past_test_item and load_app_settings(self.database_path).appEnvironment == "development"
        ):
            raise CalendarSchedulingError(
                "scheduled_for must be in the future.",
                ["scheduled_for_not_future"],
            )

    def _require_draft(self, draft_id: str) -> SavedGeneratedDraft:
        draft = get_generated_draft(self.database_path, draft_id)
        if draft is None:
            raise CalendarSchedulingError(
                f"Draft {draft_id!r} does not exist.",
                ["draft_not_found"],
            )
        return draft

    def _require_scheduled_post(self, scheduled_post_id: str) -> ScheduledPost:
        scheduled = self.get_scheduled_post(scheduled_post_id)
        if scheduled is None:
            raise CalendarSchedulingError(
                f"Scheduled post {scheduled_post_id!r} does not exist.",
                ["scheduled_post_not_found"],
            )
        return scheduled

    def _queue_for_scheduled_post(self, scheduled_post_id: str) -> PublishQueueItem | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT *
                FROM publish_queue_items
                WHERE scheduled_post_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (scheduled_post_id,),
            ).fetchone()
        return _row_to_queue_item(row) if row else None

    def _append_log(
        self,
        connection: sqlite3.Connection,
        *,
        entity_id: str,
        action: str,
        actor_label: str,
        notes: str | None,
        changed_fields: dict[str, Any],
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO approval_logs (
              id, entity_type, entity_id, action, actor_label,
              notes, changed_fields_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "scheduled_post",
                entity_id,
                action,
                actor_label,
                notes,
                _json(changed_fields),
                created_at,
            ),
        )

    def _update_generated_post_readiness(
        self,
        connection: sqlite3.Connection,
        draft_id: str,
        last_scheduled_at: str,
        readiness_status: str,
        updated_at: str,
    ) -> None:
        connection.execute(
            """
            UPDATE generated_posts
            SET last_scheduled_at = ?,
                publish_readiness_status = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (last_scheduled_at, readiness_status, updated_at, draft_id),
        )


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
