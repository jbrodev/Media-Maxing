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
from scripts.services.scheduling import CalendarSchedulingError, CalendarSchedulingService


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
            "brand-schedule-test",
            "Schedule Test Exterior Care",
            _json(["pressure washing"]),
            _json(["Demo City"]),
            _json(["Uses careful surface checks."]),
            _json([]),
            _json({"demo": True}),
        ),
    )


def _insert_media(connection: sqlite3.Connection, media_id: str = "media-schedule") -> None:
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
    caption: str = "Safe approved schedule draft.",
    media_ids: list[str] | None = None,
    safety_flags: list[str] | None = None,
) -> GeneratedContentBundle:
    return GeneratedContentBundle(
        brand_profile_id="brand-schedule-test",
        posts=[
            PlatformPostDraft(
                platform=platform,
                caption=caption,
                hashtags=["#DemoPost", "#LocalService"],
                media_asset_ids=media_ids or [],
                call_to_action="Ask about local availability.",
                safety_flags=safety_flags or [],
                content_goal="build_trust",
                content_angle="trust_builder",
            )
        ],
        prompt_id="platform_post_generator_v1",
        prompt_version="v1",
        generation_provider="mock",
        created_at="2026-05-26T18:00:00Z",
    )


class CalendarSchedulingServiceTest(unittest.TestCase):
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

    def _saved_draft(
        self,
        db_path: Path,
        *,
        platform: str = "facebook",
        media_ids: list[str] | None = None,
        safety_flags: list[str] | None = None,
        caption: str = "Safe approved schedule draft.",
    ):
        return save_generated_bundle_to_drafts(
            db_path,
            _bundle(
                platform=platform,
                media_ids=media_ids,
                safety_flags=safety_flags,
                caption=caption,
            ),
            save_request_id=f"schedule-test-{platform}-{len(safety_flags or [])}-{caption[:8]}",
        )[0]

    def test_schedule_approved_safe_draft_creates_scheduled_post_queue_item_and_log(self):
        db_path = self._database()
        draft = self._saved_draft(db_path, platform="instagram", media_ids=["media-schedule"])
        approve_generated_draft(db_path, draft.id, actor_label="owner")
        service = CalendarSchedulingService(db_path)

        scheduled = service.schedule_approved_draft(
            draft.id,
            scheduled_for="2099-06-10T13:00:00Z",
            timezone="America/New_York",
            user_notes="Post before lunch.",
            actor_label="owner",
        )

        self.assertEqual(scheduled.generatedPostId, draft.id)
        self.assertEqual(scheduled.brandProfileId, draft.brandProfileId)
        self.assertEqual(scheduled.platform, "instagram")
        self.assertEqual(scheduled.scheduledFor, "2099-06-10T13:00:00Z")
        self.assertEqual(scheduled.timezone, "America/New_York")
        self.assertEqual(scheduled.status, "scheduled")
        self.assertEqual(scheduled.captionSnapshot, draft.caption)
        self.assertEqual(scheduled.mediaAssetIds, ["media-schedule"])
        self.assertTrue(scheduled.publishQueueItemId)
        self.assertEqual(scheduled.scheduleMetadata["hashtags"], ["#DemoPost", "#LocalService"])
        self.assertEqual(scheduled.scheduleMetadata["callToAction"], "Ask about local availability.")

        queue_item = service.get_publish_queue_item(scheduled.publishQueueItemId)
        self.assertEqual(queue_item.scheduledPostId, scheduled.id)
        self.assertEqual(queue_item.queueStatus, "waiting")
        self.assertEqual(queue_item.dueAt, "2099-06-10T13:00:00Z")
        self.assertEqual(queue_item.timezone, "America/New_York")

        with closing(sqlite3.connect(db_path)) as connection:
            action = connection.execute(
                """
                SELECT action
                FROM approval_logs
                WHERE entity_type = 'scheduled_post'
                  AND entity_id = ?
                """,
                (scheduled.id,),
            ).fetchone()[0]
            readiness = connection.execute(
                """
                SELECT last_scheduled_at, publish_readiness_status
                FROM generated_posts
                WHERE id = ?
                """,
                (draft.id,),
            ).fetchone()
        self.assertEqual(action, "scheduled")
        self.assertEqual(readiness, ("2099-06-10T13:00:00Z", "waiting"))

    def test_unapproved_rejected_flagged_and_paused_drafts_cannot_schedule(self):
        db_path = self._database()
        service = CalendarSchedulingService(db_path)

        needs_review = self._saved_draft(db_path, caption="needs review")
        rejected = self._saved_draft(db_path, caption="rejected")
        reject_generated_draft(db_path, rejected.id, reason="Not useful.", actor_label="owner")
        flagged = self._saved_draft(
            db_path,
            caption="flagged",
            safety_flags=["unsupported_guarantee"],
        )
        approve_generated_draft(db_path, flagged.id, actor_label="owner")

        for draft_id, expected_code in (
            (needs_review.id, "draft_not_approved"),
            (rejected.id, "draft_rejected"),
            (flagged.id, "critical_safety_flags"),
        ):
            with self.subTest(draft_id=draft_id):
                with self.assertRaises(CalendarSchedulingError) as context:
                    service.schedule_approved_draft(
                        draft_id,
                        scheduled_for="2099-06-10T13:00:00Z",
                    )
                self.assertIn(expected_code, context.exception.error_codes)

        paused = self._saved_draft(db_path, caption="paused")
        approve_generated_draft(db_path, paused.id, actor_label="owner")
        update_app_settings(db_path, {"emergencyPauseEnabled": True})
        with self.assertRaises(CalendarSchedulingError) as context:
            service.schedule_approved_draft(
                paused.id,
                scheduled_for="2099-06-10T13:00:00Z",
            )
        self.assertIn("emergency_pause_enabled", context.exception.error_codes)

    def test_emergency_pause_blocks_rescheduling(self):
        db_path = self._database()
        draft = self._saved_draft(db_path)
        approve_generated_draft(db_path, draft.id, actor_label="owner")
        service = CalendarSchedulingService(db_path)
        scheduled = service.schedule_approved_draft(
            draft.id,
            scheduled_for="2099-06-10T13:00:00Z",
        )

        update_app_settings(db_path, {"emergencyPauseEnabled": True})

        with self.assertRaises(CalendarSchedulingError) as context:
            service.update_scheduled_time(
                scheduled.id,
                scheduled_for="2099-06-12T15:30:00Z",
                timezone="America/Chicago",
                actor_label="owner",
            )
        self.assertIn("emergency_pause_enabled", context.exception.error_codes)

    def test_reschedule_cancel_and_list_calendar_items(self):
        db_path = self._database()
        draft = self._saved_draft(db_path)
        approve_generated_draft(db_path, draft.id, actor_label="owner")
        service = CalendarSchedulingService(db_path)
        scheduled = service.schedule_approved_draft(
            draft.id,
            scheduled_for="2099-06-10T13:00:00Z",
        )

        rescheduled = service.update_scheduled_time(
            scheduled.id,
            scheduled_for="2099-06-12T15:30:00Z",
            timezone="America/Chicago",
            actor_label="owner",
        )
        self.assertEqual(rescheduled.scheduledFor, "2099-06-12T15:30:00Z")
        self.assertEqual(rescheduled.timezone, "America/Chicago")
        self.assertEqual(
            service.get_publish_queue_item(rescheduled.publishQueueItemId).dueAt,
            "2099-06-12T15:30:00Z",
        )

        noted = service.update_scheduled_notes(
            scheduled.id,
            "Move this if the crew is unavailable.",
            actor_label="owner",
        )
        self.assertEqual(noted.userNotes, "Move this if the crew is unavailable.")

        week_items = service.list_scheduled_posts(
            start="2099-06-09T00:00:00Z",
            end="2099-06-16T00:00:00Z",
        )
        self.assertEqual([item.id for item in week_items], [scheduled.id])

        canceled = service.cancel_scheduled_post(scheduled.id, actor_label="owner")
        self.assertEqual(canceled.status, "canceled")
        self.assertEqual(
            service.get_publish_queue_item(canceled.publishQueueItemId).queueStatus,
            "canceled",
        )

    def test_status_actions_update_scheduled_post_and_audit_log(self):
        db_path = self._database()
        draft = self._saved_draft(db_path)
        approve_generated_draft(db_path, draft.id, actor_label="owner")
        service = CalendarSchedulingService(db_path)
        scheduled = service.schedule_approved_draft(
            draft.id,
            scheduled_for="2099-06-10T13:00:00Z",
        )

        queued = service.mark_queued(scheduled.id, actor_label="system")
        completed = service.mark_completed(scheduled.id, actor_label="system")
        missed = service.mark_missed(scheduled.id, actor_label="system")

        self.assertEqual(queued.status, "queued")
        self.assertEqual(completed.status, "completed")
        self.assertEqual(missed.status, "missed")

        with closing(sqlite3.connect(db_path)) as connection:
            actions = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT action
                    FROM approval_logs
                    WHERE entity_type = 'scheduled_post'
                      AND entity_id = ?
                    ORDER BY rowid
                    """,
                    (scheduled.id,),
                ).fetchall()
            ]
        self.assertIn("marked_queued", actions)
        self.assertIn("marked_completed", actions)
        self.assertIn("marked_missed", actions)


if __name__ == "__main__":
    unittest.main()
