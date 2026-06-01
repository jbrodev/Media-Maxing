from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.services.preflight import (
    REQUIREMENT_VERSION,
    PreflightValidationService,
)


RUNNER_LOCK_ID = "local_job_runner"
DEFAULT_LOCK_TTL_SECONDS = 300
DEFAULT_MISSED_THRESHOLD_HOURS = 24


@dataclass(frozen=True)
class PreflightResult:
    eligible: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    requirementVersion: str = REQUIREMENT_VERSION

    @property
    def preflight_status(self) -> str:
        if self._has_error_code("emergency_pause_enabled"):
            return "blocked"
        if self.errors:
            return "errors"
        if self.warnings:
            return "warnings"
        return "passed"

    @property
    def attempt_status(self) -> str:
        if self._has_error_code("emergency_pause_enabled"):
            return "blocked"
        return "succeeded" if self.eligible else "failed"

    @property
    def error_code(self) -> str | None:
        if not self.errors:
            return None
        return _message_code(self.errors[0])

    @property
    def error_message(self) -> str | None:
        if not self.errors:
            return None
        return "; ".join(self.errors)

    def _has_error_code(self, code: str) -> bool:
        return any(_message_code(error) == code for error in self.errors)


@dataclass(frozen=True)
class JobRunSummary:
    lockAcquired: bool = True
    dueChecked: int = 0
    queueChecked: int = 0
    queueReady: int = 0
    queueBlocked: int = 0
    missedMarked: int = 0
    attemptsCreated: int = 0
    staleLocksCleaned: int = 0
    notes: list[str] = field(default_factory=list)


class LocalJobRunner:
    """Lightweight local runner for scheduled post readiness.

    The runner only updates local SQLite rows and records local preflight
    attempts. It never publishes, calls social APIs, or requires credentials.
    """

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))
        self.preflight = PreflightValidationService(self.database_path)
        self.owner = f"local-runner-{uuid.uuid4()}"

    def run_once(
        self,
        *,
        now: str | datetime | None = None,
        missed_threshold_hours: int = DEFAULT_MISSED_THRESHOLD_HOURS,
        due_soon_minutes: int = 0,
        use_lock: bool = True,
    ) -> JobRunSummary:
        now_dt = _coerce_datetime(now)
        lock_acquired = True
        if use_lock:
            lock_acquired = self.acquire_lock(now=now_dt)
            if not lock_acquired:
                return JobRunSummary(
                    lockAcquired=False,
                    notes=["Another local job runner appears to be active."],
                )

        try:
            stale_locks = self.cleanup_old_job_locks(now=now_dt)
            missed = self.mark_missed_scheduled_posts(
                now=now_dt,
                threshold_hours=missed_threshold_hours,
            )
            due_summary = self.check_due_scheduled_posts(now=now_dt)
            queue_summary = self.run_publish_queue_preflight(
                now=now_dt,
                due_soon_minutes=due_soon_minutes,
                include_blocked=False,
            )
            return JobRunSummary(
                lockAcquired=True,
                dueChecked=due_summary.dueChecked,
                queueChecked=queue_summary.queueChecked,
                queueReady=due_summary.queueReady + queue_summary.queueReady,
                queueBlocked=due_summary.queueBlocked + queue_summary.queueBlocked,
                missedMarked=missed.missedMarked,
                attemptsCreated=(
                    due_summary.attemptsCreated
                    + queue_summary.attemptsCreated
                    + missed.attemptsCreated
                ),
                staleLocksCleaned=stale_locks,
            )
        finally:
            if use_lock:
                self.release_lock()

    def check_due_scheduled_posts(
        self,
        *,
        now: str | datetime | None = None,
    ) -> JobRunSummary:
        now_dt = _coerce_datetime(now)
        due_rows = self._due_scheduled_rows(now_dt)
        ready = 0
        blocked = 0
        attempts = 0
        for row in due_rows:
            result = self._run_preflight_for_scheduled_row(row)
            attempt_created = self._apply_preflight_result(
                scheduled_row=row,
                result=result,
                now_dt=now_dt,
                update_scheduled_status=True,
            )
            attempts += int(attempt_created)
            if result.eligible:
                ready += 1
            else:
                blocked += 1
        return JobRunSummary(
            dueChecked=len(due_rows),
            queueReady=ready,
            queueBlocked=blocked,
            attemptsCreated=attempts,
        )

    def run_publish_queue_preflight(
        self,
        *,
        now: str | datetime | None = None,
        due_soon_minutes: int = 0,
        include_blocked: bool = True,
    ) -> JobRunSummary:
        now_dt = _coerce_datetime(now)
        due_before = now_dt + timedelta(minutes=max(0, due_soon_minutes))
        queue_rows = self._queue_rows_for_preflight(
            due_before,
            include_blocked=include_blocked,
        )
        checked = 0
        ready = 0
        blocked = 0
        attempts = 0
        for queue_row in queue_rows:
            scheduled_row = self._scheduled_row(queue_row["scheduled_post_id"])
            if scheduled_row is None:
                result = PreflightResult(
                    eligible=False,
                    errors=["missing_scheduled_post: Queue item has no scheduled post."],
                )
                attempt_created = self._apply_queue_only_preflight_result(
                    queue_row=queue_row,
                    result=result,
                    now_dt=now_dt,
                )
            else:
                result = self._run_preflight_for_scheduled_row(scheduled_row)
                attempt_created = self._apply_preflight_result(
                    scheduled_row=scheduled_row,
                    result=result,
                    now_dt=now_dt,
                    update_scheduled_status=_parse_iso(
                    scheduled_row["scheduled_for"]
                )
                    <= now_dt
                    and scheduled_row["status"] == "scheduled",
                )
            checked += 1
            attempts += int(attempt_created)
            if result.eligible:
                ready += 1
            else:
                blocked += 1
        return JobRunSummary(
            queueChecked=checked,
            queueReady=ready,
            queueBlocked=blocked,
            attemptsCreated=attempts,
        )

    def mark_missed_scheduled_posts(
        self,
        *,
        now: str | datetime | None = None,
        threshold_hours: int = DEFAULT_MISSED_THRESHOLD_HOURS,
    ) -> JobRunSummary:
        now_dt = _coerce_datetime(now)
        threshold_dt = now_dt - timedelta(hours=max(1, threshold_hours))
        rows = self._missed_candidate_rows(threshold_dt)
        attempts = 0
        for row in rows:
            result = PreflightResult(
                eligible=False,
                errors=[
                    "missed_threshold_exceeded: Scheduled post is overdue by the local missed threshold."
                ],
            )
            if self._apply_missed_result(row, result, now_dt):
                attempts += 1
        return JobRunSummary(missedMarked=len(rows), attemptsCreated=attempts)

    def cleanup_old_job_locks(
        self,
        *,
        now: str | datetime | None = None,
    ) -> int:
        now_iso = _utc_iso(_coerce_datetime(now))
        with closing(sqlite3.connect(self.database_path)) as connection:
            cursor = connection.execute(
                "DELETE FROM local_job_locks WHERE expires_at <= ?",
                (now_iso,),
            )
            connection.commit()
            return int(cursor.rowcount or 0)

    def acquire_lock(
        self,
        *,
        now: str | datetime | None = None,
        ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS,
    ) -> bool:
        now_dt = _coerce_datetime(now)
        now_iso = _utc_iso(now_dt)
        expires_iso = _utc_iso(now_dt + timedelta(seconds=max(30, ttl_seconds)))
        with closing(sqlite3.connect(self.database_path)) as connection:
            try:
                connection.execute("BEGIN")
                connection.execute(
                    "DELETE FROM local_job_locks WHERE expires_at <= ?",
                    (now_iso,),
                )
                connection.execute(
                    """
                    INSERT INTO local_job_locks (id, owner, locked_at, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (RUNNER_LOCK_ID, self.owner, now_iso, expires_iso),
                )
                connection.commit()
                return True
            except sqlite3.IntegrityError:
                connection.rollback()
                return False

    def release_lock(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                "DELETE FROM local_job_locks WHERE id = ? AND owner = ?",
                (RUNNER_LOCK_ID, self.owner),
            )
            connection.commit()

    def _run_preflight_for_scheduled_row(self, row: sqlite3.Row) -> PreflightResult:
        result = self.preflight.validate_scheduled_post(row["id"])
        return PreflightResult(
            eligible=result.passed,
            errors=result.errors,
            warnings=result.warnings,
            info=result.info,
            requirementVersion=result.requirementVersion,
        )

    def _apply_preflight_result(
        self,
        *,
        scheduled_row: sqlite3.Row,
        result: PreflightResult,
        now_dt: datetime,
        update_scheduled_status: bool,
    ) -> bool:
        queue_row = self._queue_row_for_scheduled(scheduled_row["id"])
        if queue_row is None:
            raise RuntimeError(
                f"Scheduled post {scheduled_row['id']} has no publish queue item."
            )

        now_iso = _utc_iso(now_dt)
        queue_status = "ready" if result.eligible else "blocked"
        scheduled_status = "queued" if result.eligible else "needs_attention"

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN")
            if update_scheduled_status:
                connection.execute(
                    """
                    UPDATE scheduled_posts
                    SET status = ?,
                        preflight_snapshot_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        scheduled_status,
                        _json(
                            {
                                "eligible": result.eligible,
                                "errors": result.errors,
                                "warnings": result.warnings,
                                "info": result.info,
                                "checkedAt": now_iso,
                                "source": "local_job_runner",
                                "requirementVersion": result.requirementVersion,
                            }
                        ),
                        now_iso,
                        scheduled_row["id"],
                    ),
                )
            connection.execute(
                """
                UPDATE publish_queue_items
                SET queue_status = ?,
                    preflight_status = ?,
                    preflight_errors_json = ?,
                    preflight_warnings_json = ?,
                    last_checked_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    queue_status,
                    result.preflight_status,
                    _json(result.errors),
                    _json(result.warnings),
                    now_iso,
                    now_iso,
                    queue_row["id"],
                ),
            )
            created = self._insert_preflight_attempt_if_changed(
                connection,
                queue_row=queue_row,
                scheduled_id=scheduled_row["id"],
                platform=scheduled_row["platform"],
                result=result,
                now_iso=now_iso,
            )
            connection.commit()
        return created

    def _apply_queue_only_preflight_result(
        self,
        *,
        queue_row: sqlite3.Row,
        result: PreflightResult,
        now_dt: datetime,
    ) -> bool:
        now_iso = _utc_iso(now_dt)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN")
            connection.execute(
                """
                UPDATE publish_queue_items
                SET queue_status = 'blocked',
                    preflight_status = ?,
                    preflight_errors_json = ?,
                    preflight_warnings_json = ?,
                    last_checked_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    result.preflight_status,
                    _json(result.errors),
                    _json(result.warnings),
                    now_iso,
                    now_iso,
                    queue_row["id"],
                ),
            )
            created = self._insert_preflight_attempt_if_changed(
                connection,
                queue_row=queue_row,
                scheduled_id=queue_row["scheduled_post_id"],
                platform=queue_row["platform"],
                result=result,
                now_iso=now_iso,
            )
            connection.commit()
        return created

    def _apply_missed_result(
        self,
        row: sqlite3.Row,
        result: PreflightResult,
        now_dt: datetime,
    ) -> bool:
        queue_row = self._queue_row_for_scheduled(row["id"])
        now_iso = _utc_iso(now_dt)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN")
            connection.execute(
                """
                UPDATE scheduled_posts
                SET status = 'missed',
                    preflight_snapshot_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    _json(
                        {
                            "eligible": False,
                            "errors": result.errors,
                            "warnings": result.warnings,
                            "info": result.info,
                            "checkedAt": now_iso,
                            "source": "local_job_runner",
                            "requirementVersion": result.requirementVersion,
                        }
                    ),
                    now_iso,
                    row["id"],
                ),
            )
            created = False
            if queue_row is not None and queue_row["queue_status"] in {"waiting", "blocked"}:
                connection.execute(
                    """
                    UPDATE publish_queue_items
                    SET queue_status = 'blocked',
                        preflight_status = 'errors',
                        preflight_errors_json = ?,
                        preflight_warnings_json = ?,
                        last_checked_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        _json(result.errors),
                        _json(result.warnings),
                        now_iso,
                        now_iso,
                        queue_row["id"],
                    ),
                )
                created = self._insert_preflight_attempt_if_changed(
                    connection,
                    queue_row=queue_row,
                    scheduled_id=row["id"],
                    platform=row["platform"],
                    result=result,
                    now_iso=now_iso,
                )
            connection.commit()
        return created

    def _insert_preflight_attempt_if_changed(
        self,
        connection: sqlite3.Connection,
        *,
        queue_row: sqlite3.Row,
        scheduled_id: str,
        platform: str,
        result: PreflightResult,
        now_iso: str,
    ) -> bool:
        latest = connection.execute(
            """
            SELECT attempt_status, error_code, error_message
            FROM publish_attempts
            WHERE publish_queue_item_id = ?
              AND attempt_type = 'preflight'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (queue_row["id"],),
        ).fetchone()
        next_signature = (
            result.attempt_status,
            result.error_code,
            result.error_message,
        )
        if latest is not None and tuple(latest) == next_signature:
            return False

        connection.execute(
            """
            INSERT INTO publish_attempts (
              id, publish_queue_item_id, scheduled_post_id, platform,
              attempt_type, attempt_status, started_at, finished_at,
              error_code, error_message, provider_response_json, created_at
            ) VALUES (?, ?, ?, ?, 'preflight', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                queue_row["id"],
                scheduled_id,
                platform,
                result.attempt_status,
                now_iso,
                now_iso,
                result.error_code,
                result.error_message,
                _json(
                    {
                        "source": "local_job_runner",
                        "realPublishing": False,
                        "errors": result.errors,
                        "warnings": result.warnings,
                        "info": result.info,
                        "requirementVersion": result.requirementVersion,
                    }
                ),
                now_iso,
            ),
        )
        return True

    def _due_scheduled_rows(self, now_dt: datetime) -> list[sqlite3.Row]:
        now_iso = _utc_iso(now_dt)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM scheduled_posts
                WHERE status = 'scheduled'
                  AND scheduled_for <= ?
                ORDER BY scheduled_for ASC, created_at ASC
                """,
                (now_iso,),
            ).fetchall()
        return list(rows)

    def _queue_rows_for_preflight(
        self,
        due_before: datetime,
        *,
        include_blocked: bool,
    ) -> list[sqlite3.Row]:
        due_before_iso = _utc_iso(due_before)
        statuses = ("waiting", "blocked") if include_blocked else ("waiting",)
        placeholders = ", ".join("?" for _ in statuses)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                f"""
                SELECT *
                FROM publish_queue_items
                WHERE queue_status IN ({placeholders})
                  AND due_at <= ?
                ORDER BY due_at ASC, created_at ASC
                """,
                (*statuses, due_before_iso),
            ).fetchall()
        return list(rows)

    def _missed_candidate_rows(self, threshold_dt: datetime) -> list[sqlite3.Row]:
        threshold_iso = _utc_iso(threshold_dt)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM scheduled_posts
                WHERE status IN ('scheduled', 'needs_attention', 'failed')
                  AND scheduled_for <= ?
                ORDER BY scheduled_for ASC, created_at ASC
                """,
                (threshold_iso,),
            ).fetchall()
        return list(rows)

    def _scheduled_row(self, scheduled_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT * FROM scheduled_posts WHERE id = ?",
                (scheduled_id,),
            ).fetchone()

    def _queue_row_for_scheduled(self, scheduled_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                """
                SELECT *
                FROM publish_queue_items
                WHERE scheduled_post_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (scheduled_id,),
            ).fetchone()

    def _brand_exists(self, brand_profile_id: str) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT 1 FROM brand_profiles WHERE id = ?",
                (brand_profile_id,),
            ).fetchone()
        return row is not None

    def _missing_media_ids(self, media_ids: list[str]) -> list[str]:
        if not media_ids:
            return []
        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute(
                f"""
                SELECT id
                FROM media_assets
                WHERE id IN ({', '.join('?' for _ in media_ids)})
                """,
                tuple(media_ids),
            ).fetchall()
        existing = {row[0] for row in rows}
        return [media_id for media_id in media_ids if media_id not in existing]

    def _connected_account_exists(self, platform: str) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'social_accounts'"
            ).fetchone()
            if table is None:
                return False
            row = connection.execute(
                """
                SELECT 1
                FROM social_accounts
                WHERE platform = ?
                  AND status IN ('connected', 'mock_connected', 'ready')
                LIMIT 1
                """,
                (platform,),
            ).fetchone()
        return row is not None


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


def _parse_iso(raw_value: str) -> datetime:
    normalized = raw_value.strip()
    parse_value = normalized[:-1] + "+00:00" if normalized.endswith("Z") else normalized
    parsed = datetime.fromisoformat(parse_value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _coerce_datetime(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(microsecond=0)
    return _parse_iso(value).replace(microsecond=0)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _message_code(message: str) -> str:
    return message.split(":", 1)[0]


def _dedupe_messages(messages: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for message in messages:
        if message in seen:
            continue
        seen.add(message)
        deduped.append(message)
    return deduped


def _print_summary(summary: JobRunSummary) -> None:
    print("Local job runner completed.")
    print(f"  lock_acquired: {summary.lockAcquired}")
    print(f"  due_checked: {summary.dueChecked}")
    print(f"  queue_checked: {summary.queueChecked}")
    print(f"  queue_ready: {summary.queueReady}")
    print(f"  queue_blocked: {summary.queueBlocked}")
    print(f"  missed_marked: {summary.missedMarked}")
    print(f"  attempts_created: {summary.attemptsCreated}")
    print(f"  stale_locks_cleaned: {summary.staleLocksCleaned}")
    for note in summary.notes:
        print(f"  note: {note}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run local scheduled-post readiness jobs. This updates SQLite only; "
            "it never publishes to social platforms."
        )
    )
    parser.add_argument(
        "--database",
        help="Path to the SQLite database. Defaults to DATABASE_URL or data/app.sqlite.",
    )
    parser.add_argument("--once", action="store_true", help="Run one local job pass.")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run repeatedly for local development. Stop with Ctrl+C.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=30,
        help="Delay between --watch runs. Defaults to 30 seconds.",
    )
    parser.add_argument(
        "--now",
        help="Override the current UTC time with an ISO timestamp for verification.",
    )
    parser.add_argument(
        "--missed-threshold-hours",
        type=int,
        default=DEFAULT_MISSED_THRESHOLD_HOURS,
        help="Hours after due time before a scheduled post is marked missed.",
    )
    args = parser.parse_args()

    if not args.once and not args.watch:
        parser.error("Choose --once or --watch.")

    runner = LocalJobRunner(args.database)

    if args.once:
        _print_summary(
            runner.run_once(
                now=args.now,
                missed_threshold_hours=args.missed_threshold_hours,
            )
        )
        return

    try:
        while True:
            _print_summary(
                runner.run_once(
                    now=args.now,
                    missed_threshold_hours=args.missed_threshold_hours,
                )
            )
            time.sleep(max(5, args.interval_seconds))
    except KeyboardInterrupt:
        print("Local job runner stopped.")


if __name__ == "__main__":
    main()
