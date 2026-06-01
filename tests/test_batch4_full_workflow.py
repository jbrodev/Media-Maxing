from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.ai.schemas import GeneratedContentBundle, PlatformPostDraft
from scripts.db.drafts import (
    approve_generated_draft,
    reject_generated_draft,
    save_generated_bundle_to_drafts,
)
from scripts.db.init_db import initialize_database
from scripts.db.settings import update_app_settings
from scripts.jobs.local_runner import LocalJobRunner
from scripts.services.manual_export import ManualExportService
from scripts.services.publish_queue import PublishQueueError, PublishQueueService
from scripts.services.scheduling import CalendarSchedulingError, CalendarSchedulingService


def _json(value):
    return json.dumps(value, sort_keys=True)


class Batch4FullWorkflowTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        update_app_settings(
            db_path,
            {
                "localDataDirectory": str(Path(temp_dir.name) / "data"),
                "appEnvironment": "development",
            },
        )
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO brand_profiles (
                  id, business_name, services_json, locations_json,
                  supported_claims_json, blocked_phrases_json, preferences_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "brand-batch4",
                    "Batch 4 Demo Exterior Care",
                    _json(["driveway cleaning", "gutter cleaning"]),
                    _json(["Demo City"]),
                    _json(["Uses careful local service checks."]),
                    _json([]),
                    _json({"demo": True}),
                ),
            )
            connection.execute(
                """
                INSERT INTO media_assets (
                  id, media_type, original_path, file_name, mime_type,
                  file_size_bytes, tags_json, job_context_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "media-batch4-image",
                    "image",
                    "data/media/originals/batch4-demo-driveway.jpg",
                    "batch4-demo-driveway.jpg",
                    "image/jpeg",
                    2048,
                    _json(["demo", "driveway"]),
                    _json({"serviceType": "driveway cleaning"}),
                    _json({"demo": True}),
                ),
            )
            connection.commit()
        return db_path

    def _save_draft(
        self,
        db_path: Path,
        *,
        platform: str = "facebook",
        approval_status: str = "approved",
        media_ids: list[str] | None = None,
        safety_flags: list[str] | None = None,
        caption: str = "Safe Batch 4 workflow caption for local testing.",
    ):
        draft = save_generated_bundle_to_drafts(
            db_path,
            GeneratedContentBundle(
                brand_profile_id="brand-batch4",
                posts=[
                    PlatformPostDraft(
                        platform=platform,
                        headline="Batch 4 workflow post",
                        hook="A clean local scheduling workflow.",
                        caption=caption,
                        hashtags=["#DemoBusiness", "#LocalService"],
                        media_asset_ids=media_ids or [],
                        call_to_action="Ask about local exterior care.",
                        safety_flags=safety_flags or [],
                        content_goal="build_trust",
                        content_angle="trust_builder",
                    )
                ],
                prompt_id="platform_post_generator_v1",
                prompt_version="v1",
                generation_provider="mock",
                created_at="2026-05-26T18:00:00Z",
            ),
            save_request_id=f"batch4-{platform}-{approval_status}-{caption[:12]}-{len(safety_flags or [])}",
        )[0]
        if approval_status == "approved":
            return approve_generated_draft(db_path, draft.id, actor_label="owner")
        if approval_status == "rejected":
            return reject_generated_draft(
                db_path,
                draft.id,
                reason="Demo rejection.",
                actor_label="owner",
            )
        return draft

    def _row(self, db_path: Path, table: str, item_id: str):
        with closing(sqlite3.connect(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                f"SELECT * FROM {table} WHERE id = ?",
                (item_id,),
            ).fetchone()

    def _attempts(self, db_path: Path, queue_id: str) -> list[sqlite3.Row]:
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

    def test_approved_draft_to_schedule_ready_export_and_manual_completion(self):
        db_path = self._database()
        draft = self._save_draft(db_path, media_ids=["media-batch4-image"])

        scheduled = CalendarSchedulingService(db_path).schedule_approved_draft(
            draft.id,
            scheduled_for="2026-06-10T13:00:00Z",
            timezone="America/New_York",
            user_notes="Batch 4 integration test.",
            allow_past_test_item=True,
        )
        queue_id = scheduled.publishQueueItemId
        self.assertTrue(queue_id)
        self.assertEqual(self._row(db_path, "scheduled_posts", scheduled.id)["status"], "scheduled")
        self.assertEqual(self._row(db_path, "publish_queue_items", queue_id)["queue_status"], "waiting")

        runner_summary = LocalJobRunner(db_path).run_once(now="2026-06-10T13:05:00Z")
        self.assertEqual(runner_summary.queueReady, 1)
        self.assertEqual(self._row(db_path, "scheduled_posts", scheduled.id)["status"], "queued")
        queue_row = self._row(db_path, "publish_queue_items", queue_id)
        self.assertEqual(queue_row["queue_status"], "ready")
        self.assertEqual(queue_row["preflight_status"], "warnings")
        self.assertEqual(self._attempts(db_path, queue_id)[0]["attempt_type"], "preflight")

        export_result = ManualExportService(db_path).export_queue_item(
            queue_id,
            exported_at="2026-06-10T14:00:00Z",
        )
        self.assertTrue((export_result.exportPath / "metadata.json").exists())
        self.assertEqual(self._row(db_path, "publish_queue_items", queue_id)["queue_status"], "ready")

        queue_service = PublishQueueService(db_path)
        completed = queue_service.mark_manually_exported(
            queue_id,
            actor_label="owner",
            notes="Owner posted manually from export package.",
        )
        self.assertEqual(completed.queueStatus, "manually_exported")
        self.assertEqual(self._row(db_path, "scheduled_posts", scheduled.id)["status"], "completed")
        attempts = self._attempts(db_path, queue_id)
        self.assertEqual(
            sorted(attempt["attempt_type"] for attempt in attempts),
            ["manual_export", "preflight"],
        )
        manual_export_attempt = [
            attempt for attempt in attempts if attempt["attempt_type"] == "manual_export"
        ][0]
        self.assertEqual(manual_export_attempt["attempt_status"], "succeeded")

    def test_unapproved_rejected_flagged_and_paused_drafts_cannot_schedule(self):
        db_path = self._database()
        service = CalendarSchedulingService(db_path)
        cases = [
            (
                self._save_draft(db_path, approval_status="needs_review", caption="Needs review"),
                "draft_not_approved",
            ),
            (
                self._save_draft(db_path, approval_status="rejected", caption="Rejected"),
                "draft_rejected",
            ),
            (
                self._save_draft(
                    db_path,
                    caption="Flagged",
                    safety_flags=["unsupported_guarantee"],
                ),
                "critical_safety_flags",
            ),
        ]
        for draft, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(CalendarSchedulingError) as error:
                    service.schedule_approved_draft(
                        draft.id,
                        scheduled_for="2026-06-10T13:00:00Z",
                        allow_past_test_item=True,
                    )
                self.assertIn(expected_code, error.exception.error_codes)

        paused = self._save_draft(db_path, caption="Paused")
        update_app_settings(db_path, {"emergencyPauseEnabled": True})
        with self.assertRaises(CalendarSchedulingError) as error:
            service.schedule_approved_draft(
                paused.id,
                scheduled_for="2026-06-10T13:00:00Z",
                allow_past_test_item=True,
            )
        self.assertIn("emergency_pause_enabled", error.exception.error_codes)

    def test_blocked_and_canceled_queue_items_cannot_mock_publish(self):
        db_path = self._database()
        draft = self._save_draft(
            db_path,
            platform="facebook",
            caption="Facebook warning-only preflight is not enough for mock publish.",
        )
        scheduled = CalendarSchedulingService(db_path).schedule_approved_draft(
            draft.id,
            scheduled_for="2026-06-10T13:00:00Z",
            allow_past_test_item=True,
        )
        queue_id = scheduled.publishQueueItemId
        LocalJobRunner(db_path).run_once(now="2026-06-10T13:05:00Z")

        queue_service = PublishQueueService(db_path)
        with self.assertRaises(PublishQueueError) as blocked_error:
            queue_service.mock_publish(queue_id)
        self.assertIn("preflight_not_passed", blocked_error.exception.error_codes)

        CalendarSchedulingService(db_path).cancel_scheduled_post(scheduled.id)
        with self.assertRaises(PublishQueueError) as canceled_error:
            queue_service.mock_publish(queue_id)
        self.assertIn("queue_not_ready", canceled_error.exception.error_codes)

    def test_duplicate_scheduling_uses_distinct_records_and_snapshots(self):
        db_path = self._database()
        draft = self._save_draft(db_path, media_ids=["media-batch4-image"])
        service = CalendarSchedulingService(db_path)

        first = service.schedule_approved_draft(
            draft.id,
            scheduled_for="2026-06-10T13:00:00Z",
            allow_past_test_item=True,
        )
        second = service.schedule_approved_draft(
            draft.id,
            scheduled_for="2026-06-11T13:00:00Z",
            allow_past_test_item=True,
        )

        self.assertNotEqual(first.id, second.id)
        self.assertNotEqual(first.publishQueueItemId, second.publishQueueItemId)
        self.assertEqual(first.captionSnapshot, "Safe Batch 4 workflow caption for local testing.")
        self.assertEqual(second.captionSnapshot, "Safe Batch 4 workflow caption for local testing.")


if __name__ == "__main__":
    unittest.main()
