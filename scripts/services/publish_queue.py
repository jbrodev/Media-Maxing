from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.settings import load_app_settings


READY_PREFLIGHT_STATUSES = {"passed", "warnings"}
FINAL_QUEUE_STATUSES = {"mock_published", "manually_exported", "canceled", "skipped"}


class PublishQueueError(ValueError):
    def __init__(self, message: str, error_codes: list[str] | None = None):
        super().__init__(message)
        self.error_codes = error_codes or []


@dataclass(frozen=True)
class QueueActionResult:
    id: str
    scheduledPostId: str
    queueStatus: str
    preflightStatus: str
    attemptId: str | None = None
    warnings: list[str] = field(default_factory=list)


class PublishQueueService:
    """Local-only queue actions for manual export and mock publishing.

    This service updates SQLite records and writes local publish attempts. It
    never calls external APIs or creates real social posts.
    """

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))

    def mark_manually_exported(
        self,
        queue_item_id: str,
        *,
        actor_label: str = "local_user",
        notes: str | None = None,
    ) -> QueueActionResult:
        queue_row = self._require_queue_row(queue_item_id)
        scheduled_row = self._require_scheduled_row(queue_row["scheduled_post_id"])
        self._ensure_not_emergency_paused("manual export completion")
        if queue_row["queue_status"] in {"canceled", "skipped"}:
            raise PublishQueueError(
                "Canceled or skipped queue items cannot be marked manually exported.",
                ["queue_not_exportable"],
            )
        if queue_row["queue_status"] in {"mock_published", "manually_exported"}:
            raise PublishQueueError(
                "Queue item has already been completed.",
                ["queue_already_completed"],
            )
        if queue_row["preflight_status"] not in READY_PREFLIGHT_STATUSES:
            raise PublishQueueError(
                "Manual export completion requires passed or warning-only preflight.",
                ["preflight_not_ready"],
            )

        now = _now_utc()
        attempt_id = str(uuid.uuid4())
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN")
            connection.execute(
                """
                UPDATE publish_queue_items
                SET queue_status = 'manually_exported',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, queue_row["id"]),
            )
            connection.execute(
                """
                UPDATE scheduled_posts
                SET status = 'completed',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, scheduled_row["id"]),
            )
            connection.execute(
                """
                INSERT INTO publish_attempts (
                  id, publish_queue_item_id, scheduled_post_id, platform,
                  attempt_type, attempt_status, started_at, finished_at,
                  provider_response_json, created_at
                ) VALUES (?, ?, ?, ?, 'manual_export', 'succeeded', ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    queue_row["id"],
                    scheduled_row["id"],
                    queue_row["platform"],
                    now,
                    now,
                    _json(
                        {
                            "source": "publish_queue_service",
                            "actorLabel": actor_label,
                            "notes": notes,
                            "realPublishing": False,
                            "manualExportOnly": True,
                        }
                    ),
                    now,
                ),
            )
            connection.commit()

        return self._result(queue_row["id"], attempt_id=attempt_id)

    def mock_publish(
        self,
        queue_item_id: str,
        *,
        actor_label: str = "local_user",
    ) -> QueueActionResult:
        queue_row = self._require_queue_row(queue_item_id)
        scheduled_row = self._require_scheduled_row(queue_row["scheduled_post_id"])
        self._ensure_not_emergency_paused("mock publish")
        if queue_row["queue_status"] != "ready":
            raise PublishQueueError(
                "Only ready queue items can be mock-published.",
                ["queue_not_ready"],
            )
        if queue_row["preflight_status"] != "passed":
            raise PublishQueueError(
                "Mock publish requires fully passed preflight.",
                ["preflight_not_passed"],
            )
        if not bool(queue_row["mock_publish_enabled"]):
            raise PublishQueueError(
                "Mock publishing is disabled for this queue item.",
                ["mock_publish_disabled"],
            )

        now = _now_utc()
        attempt_id = str(uuid.uuid4())
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN")
            connection.execute(
                """
                UPDATE publish_queue_items
                SET queue_status = 'mock_published',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, queue_row["id"]),
            )
            connection.execute(
                """
                UPDATE scheduled_posts
                SET status = 'completed',
                    updated_at = ?
                WHERE id = ?
                """,
                (now, scheduled_row["id"]),
            )
            connection.execute(
                """
                INSERT INTO publish_attempts (
                  id, publish_queue_item_id, scheduled_post_id, platform,
                  attempt_type, attempt_status, started_at, finished_at,
                  provider_response_json, created_at
                ) VALUES (?, ?, ?, ?, 'mock_publish', 'succeeded', ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    queue_row["id"],
                    scheduled_row["id"],
                    queue_row["platform"],
                    now,
                    now,
                    _json(
                        {
                            "source": "publish_queue_service",
                            "actorLabel": actor_label,
                            "realPublishing": False,
                            "mockOnly": True,
                        }
                    ),
                    now,
                ),
            )
            connection.commit()

        return self._result(queue_row["id"], attempt_id=attempt_id)

    def _ensure_not_emergency_paused(self, action: str) -> None:
        if load_app_settings(self.database_path).emergencyPauseEnabled:
            raise PublishQueueError(
                f"Emergency pause blocks {action}.",
                ["emergency_pause_enabled"],
            )

    def _result(self, queue_item_id: str, *, attempt_id: str | None = None) -> QueueActionResult:
        row = self._require_queue_row(queue_item_id)
        return QueueActionResult(
            id=row["id"],
            scheduledPostId=row["scheduled_post_id"],
            queueStatus=row["queue_status"],
            preflightStatus=row["preflight_status"],
            attemptId=attempt_id,
            warnings=_decode_json(row["preflight_warnings_json"], []),
        )

    def _require_queue_row(self, queue_item_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM publish_queue_items WHERE id = ?",
                (queue_item_id,),
            ).fetchone()
        if row is None:
            raise PublishQueueError(
                f"Publish queue item {queue_item_id!r} does not exist.",
                ["queue_item_not_found"],
            )
        return row

    def _require_scheduled_row(self, scheduled_post_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM scheduled_posts WHERE id = ?",
                (scheduled_post_id,),
            ).fetchone()
        if row is None:
            raise PublishQueueError(
                f"Scheduled post {scheduled_post_id!r} does not exist.",
                ["scheduled_post_not_found"],
            )
        return row


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


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
