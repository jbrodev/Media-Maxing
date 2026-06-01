from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.ai.schemas import GeneratedContentBundle, PlatformPostDraft
from scripts.db.drafts import approve_generated_draft, save_generated_bundle_to_drafts
from scripts.db.init_db import initialize_database
from scripts.db.settings import update_app_settings
from scripts.jobs.local_runner import LocalJobRunner
from scripts.services.preflight import REQUIREMENT_VERSION
from scripts.services.scheduling import CalendarSchedulingService


def _json(value):
    return json.dumps(value, sort_keys=True)


def _insert_brand(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO brand_profiles (
          id, business_name, services_json, locations_json,
          supported_claims_json, blocked_phrases_json, preferences_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "brand-job-runner-test",
            "Job Runner Test Exterior Care",
            _json(["pressure washing"]),
            _json(["Demo City"]),
            _json(["Uses careful surface checks."]),
            _json([]),
            _json({"demo": True}),
        ),
    )


def _insert_media(connection: sqlite3.Connection, media_id: str = "media-job-runner") -> None:
    connection.execute(
        """
        INSERT INTO media_assets (
          id, media_type, original_path, file_name, mime_type,
          file_size_bytes, tags_json, job_context_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            media_id,
            "image",
            f"data/media/originals/{media_id}.jpg",
            f"{media_id}.jpg",
            "image/jpeg",
            1200,
            _json(["demo"]),
            _json({}),
            _json({"demo": True}),
        ),
    )


def _bundle(
    *,
    platform: str = "facebook",
    caption: str = "Safe approved local job runner draft.",
    media_ids: list[str] | None = None,
) -> GeneratedContentBundle:
    return GeneratedContentBundle(
        brand_profile_id="brand-job-runner-test",
        posts=[
            PlatformPostDraft(
                platform=platform,
                caption=caption,
                headline="Fresh curb appeal",
                hook="A quick exterior refresh can change the first impression.",
                hashtags=["#DemoPost", "#LocalService"],
                media_asset_ids=media_ids or [],
                call_to_action="Ask about local availability.",
                safety_flags=[],
                content_goal="build_trust",
                content_angle="trust_builder",
            )
        ],
        prompt_id="platform_post_generator_v1",
        prompt_version="v1",
        generation_provider="mock",
        created_at="2026-05-26T18:00:00Z",
    )


class LocalJobRunnerTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        with closing(sqlite3.connect(db_path)) as connection:
            _insert_brand(connection)
            _insert_media(connection)
            connection.commit()
        return db_path

    def _approved_draft(
        self,
        db_path: Path,
        *,
        platform: str = "facebook",
        media_ids: list[str] | None = None,
        caption: str = "Safe approved local job runner draft.",
    ):
        draft = save_generated_bundle_to_drafts(
            db_path,
            _bundle(platform=platform, media_ids=media_ids, caption=caption),
            save_request_id=f"job-runner-{platform}-{caption[:10]}-{len(media_ids or [])}",
        )[0]
        return approve_generated_draft(db_path, draft.id, actor_label="owner")

    def _schedule(
        self,
        db_path: Path,
        *,
        platform: str = "facebook",
        media_ids: list[str] | None = None,
        scheduled_for: str = "2026-01-01T12:00:00Z",
    ):
        draft = self._approved_draft(db_path, platform=platform, media_ids=media_ids)
        return CalendarSchedulingService(db_path).schedule_approved_draft(
            draft.id,
            scheduled_for=scheduled_for,
            allow_past_test_item=True,
        )

    def _row(self, db_path: Path, table: str, item_id: str):
        with closing(sqlite3.connect(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (item_id,),
            ).fetchone()

    def _attempts(self, db_path: Path, queue_id: str):
        with closing(sqlite3.connect(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                """
                SELECT *
                FROM publish_attempts
                WHERE publish_queue_item_id = ?
                ORDER BY created_at, id
                """,
                (queue_id,),
            ).fetchall()

    def test_due_safe_scheduled_post_becomes_queued_and_ready(self):
        db_path = self._database()
        scheduled = self._schedule(db_path)

        summary = LocalJobRunner(db_path).run_once(now="2026-01-01T12:05:00Z")

        scheduled_row = self._row(db_path, "scheduled_posts", scheduled.id)
        queue_row = self._row(db_path, "publish_queue_items", scheduled.publishQueueItemId)
        attempts = self._attempts(db_path, scheduled.publishQueueItemId)
        self.assertEqual(summary.dueChecked, 1)
        self.assertEqual(summary.queueReady, 1)
        self.assertEqual(scheduled_row["status"], "queued")
        self.assertEqual(queue_row["queue_status"], "ready")
        self.assertEqual(queue_row["preflight_status"], "warnings")
        self.assertIn("missing_connected_account", queue_row["preflight_warnings_json"])
        self.assertEqual(attempts[0]["attempt_type"], "preflight")
        self.assertEqual(attempts[0]["attempt_status"], "succeeded")
        provider_response = json.loads(attempts[0]["provider_response_json"])
        self.assertEqual(provider_response["requirementVersion"], REQUIREMENT_VERSION)

    def test_future_scheduled_post_remains_waiting(self):
        db_path = self._database()
        scheduled = self._schedule(db_path, scheduled_for="2026-01-02T12:00:00Z")

        summary = LocalJobRunner(db_path).run_once(now="2026-01-01T12:05:00Z")

        scheduled_row = self._row(db_path, "scheduled_posts", scheduled.id)
        queue_row = self._row(db_path, "publish_queue_items", scheduled.publishQueueItemId)
        self.assertEqual(summary.dueChecked, 0)
        self.assertEqual(scheduled_row["status"], "scheduled")
        self.assertEqual(queue_row["queue_status"], "waiting")
        self.assertEqual(len(self._attempts(db_path, scheduled.publishQueueItemId)), 0)

    def test_emergency_pause_blocks_readiness(self):
        db_path = self._database()
        scheduled = self._schedule(db_path)
        update_app_settings(db_path, {"emergencyPauseEnabled": True})

        summary = LocalJobRunner(db_path).run_once(now="2026-01-01T12:05:00Z")

        scheduled_row = self._row(db_path, "scheduled_posts", scheduled.id)
        queue_row = self._row(db_path, "publish_queue_items", scheduled.publishQueueItemId)
        attempts = self._attempts(db_path, scheduled.publishQueueItemId)
        self.assertEqual(summary.queueBlocked, 1)
        self.assertEqual(scheduled_row["status"], "needs_attention")
        self.assertEqual(queue_row["queue_status"], "blocked")
        self.assertEqual(queue_row["preflight_status"], "blocked")
        self.assertIn("emergency_pause_enabled", queue_row["preflight_errors_json"])
        self.assertEqual(attempts[0]["attempt_status"], "blocked")

    def test_critical_safety_flag_blocks_readiness(self):
        db_path = self._database()
        scheduled = self._schedule(db_path)
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                "UPDATE generated_posts SET safety_flags_json = ? WHERE id = ?",
                (_json(["unsupported_guarantee"]), scheduled.generatedPostId),
            )
            connection.commit()

        LocalJobRunner(db_path).run_once(now="2026-01-01T12:05:00Z")

        queue_row = self._row(db_path, "publish_queue_items", scheduled.publishQueueItemId)
        self.assertEqual(queue_row["queue_status"], "blocked")
        self.assertIn("critical_safety_flags", queue_row["preflight_errors_json"])

    def test_missing_media_blocks_media_required_platform(self):
        db_path = self._database()
        scheduled = self._schedule(
            db_path,
            platform="instagram",
            media_ids=["media-job-runner"],
        )
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute("DELETE FROM media_assets WHERE id = ?", ("media-job-runner",))
            connection.commit()

        LocalJobRunner(db_path).run_once(now="2026-01-01T12:05:00Z")

        queue_row = self._row(db_path, "publish_queue_items", scheduled.publishQueueItemId)
        self.assertEqual(queue_row["queue_status"], "blocked")
        self.assertIn("missing_linked_media", queue_row["preflight_errors_json"])

    def test_repeated_runs_do_not_duplicate_preflight_attempts_for_ready_item(self):
        db_path = self._database()
        scheduled = self._schedule(db_path)
        runner = LocalJobRunner(db_path)

        runner.run_once(now="2026-01-01T12:05:00Z")
        runner.run_once(now="2026-01-01T12:10:00Z")

        attempts = self._attempts(db_path, scheduled.publishQueueItemId)
        self.assertEqual(len(attempts), 1)

    def test_missed_threshold_marks_very_old_scheduled_post_missed(self):
        db_path = self._database()
        scheduled = self._schedule(db_path, scheduled_for="2026-01-01T12:00:00Z")

        summary = LocalJobRunner(db_path).run_once(now="2026-01-03T13:00:00Z")

        scheduled_row = self._row(db_path, "scheduled_posts", scheduled.id)
        queue_row = self._row(db_path, "publish_queue_items", scheduled.publishQueueItemId)
        self.assertEqual(summary.missedMarked, 1)
        self.assertEqual(scheduled_row["status"], "missed")
        self.assertEqual(queue_row["queue_status"], "blocked")
        self.assertIn("missed_threshold_exceeded", queue_row["preflight_errors_json"])


if __name__ == "__main__":
    unittest.main()
