from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.ai.schemas import GeneratedContentBundle, PlatformPostDraft
from scripts.db.drafts import save_generated_bundle_to_drafts
from scripts.db.init_db import initialize_database
from scripts.db.settings import update_app_settings
from scripts.services.approval_queue import (
    Actor,
    ApprovalQueueService,
    CRITICAL_SAFETY_FLAGS,
)


def _json(value):
    return json.dumps(value, sort_keys=True)


def _insert_brand(connection: sqlite3.Connection, brand_id: str = "brand-approval") -> None:
    connection.execute(
        """
        INSERT INTO brand_profiles (
          id,
          business_name,
          services_json,
          locations_json,
          supported_claims_json,
          blocked_phrases_json,
          preferences_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            brand_id,
            "Approval Gate Exterior Demo",
            _json(["pressure washing"]),
            _json(["Demo City"]),
            _json(["Uses careful surface checks."]),
            _json([]),
            _json({"demo": True}),
        ),
    )


def _insert_media(connection: sqlite3.Connection, media_id: str = "media-approved") -> None:
    connection.execute(
        """
        INSERT INTO media_assets (
          id,
          media_type,
          original_path,
          file_name,
          mime_type,
          file_size_bytes,
          tags_json,
          job_context_json,
          metadata_json
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
    caption: str = "Safe approved draft caption.",
    media_ids: list[str] | None = None,
    safety_flags: list[str] | None = None,
    brand_id: str = "brand-approval",
) -> GeneratedContentBundle:
    return GeneratedContentBundle(
        brand_profile_id=brand_id,
        posts=[
            PlatformPostDraft(
                platform=platform,
                caption=caption,
                hashtags=["#DemoPost"],
                media_asset_ids=media_ids or [],
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


class ApprovalQueueServiceTest(unittest.TestCase):
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
        caption: str = "Safe approved draft caption.",
    ):
        return save_generated_bundle_to_drafts(
            db_path,
            _bundle(
                platform=platform,
                media_ids=media_ids,
                safety_flags=safety_flags,
                caption=caption,
            ),
            save_request_id=f"approval-test-{platform}-{len(safety_flags or [])}-{caption[:8]}",
        )[0]

    def test_lists_needing_review_and_approved_drafts(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        first = self._saved_draft(db_path)
        second = self._saved_draft(db_path, platform="linkedin")

        self.assertEqual(
            {draft.id for draft in service.list_drafts_needing_review()},
            {first.id, second.id},
        )

        service.approve(first.id, actor=Actor(actorType="user", actorName="Owner"))
        approved_ids = [draft.id for draft in service.list_approved_drafts()]
        self.assertIn(first.id, approved_ids)
        self.assertNotIn(second.id, approved_ids)
        self.assertEqual(service.get_approval_status(first.id), "approved")

    def test_approval_actions_create_structured_log_entries(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(db_path)

        service.approve(draft.id, actor=Actor(actorType="user", actorName="Owner"))
        service.reject(
            draft.id,
            reason="Offer is no longer current.",
            actor=Actor(actorType="test", actorName="Unit Test"),
        )
        service.request_revision(
            draft.id,
            reason="Make the CTA softer.",
            actor=Actor(actorType="ai", actorName="Mock Reviewer"),
        )
        archived = service.archive(
            draft.id,
            reason="Keep historical record.",
            actor=Actor(actorType="system", actorName="Local System"),
        )

        self.assertEqual(archived.approvalStatus, "archived")
        history = service.get_approval_history(draft.id)
        last = history[-1]
        self.assertEqual(last.draftId, draft.id)
        self.assertEqual(last.action, "archived")
        self.assertEqual(last.previousStatus, "revision_requested")
        self.assertEqual(last.newStatus, "archived")
        self.assertEqual(last.reason, "Keep historical record.")
        self.assertEqual(last.actorType, "system")
        self.assertEqual(last.actorName, "Local System")
        self.assertTrue(last.createdAt)

    def test_approved_safe_draft_is_eligible_for_scheduling(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(db_path, platform="instagram", media_ids=["media-approved"])
        service.approve(draft.id, actor=Actor(actorType="user", actorName="Owner"))

        result = service.check_scheduling_eligibility(draft.id)

        self.assertTrue(result.eligible)
        self.assertEqual(result.errors, [])

    def test_draft_needing_review_is_not_eligible(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(db_path)

        result = service.check_scheduling_eligibility(draft.id)

        self.assertFalse(result.eligible)
        self.assertIn("draft_not_approved", result.error_codes)

    def test_rejected_draft_is_not_eligible(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(db_path)
        service.reject(draft.id, reason="Not useful.", actor=Actor(actorType="user"))

        result = service.check_scheduling_eligibility(draft.id)

        self.assertFalse(result.eligible)
        self.assertIn("draft_rejected", result.error_codes)

    def test_critical_safety_flag_blocks_scheduling_and_publishing(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(
            db_path,
            safety_flags=["unsupported_guarantee"],
        )
        service.approve(draft.id, actor=Actor(actorType="user"))

        scheduling = service.check_scheduling_eligibility(draft.id)
        publishing = service.check_publishing_eligibility(draft.id)

        self.assertIn("unsupported_guarantee", CRITICAL_SAFETY_FLAGS)
        self.assertFalse(scheduling.eligible)
        self.assertFalse(publishing.eligible)
        self.assertIn("critical_safety_flags", scheduling.error_codes)
        self.assertIn("critical_safety_flags", publishing.error_codes)

    def test_emergency_pause_blocks_scheduling_and_publishing(self):
        db_path = self._database()
        update_app_settings(db_path, {"emergencyPauseEnabled": True})
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(db_path)
        service.approve(draft.id, actor=Actor(actorType="user"))

        scheduling = service.check_scheduling_eligibility(draft.id)
        publishing = service.check_publishing_eligibility(draft.id)

        self.assertFalse(scheduling.eligible)
        self.assertFalse(publishing.eligible)
        self.assertIn("emergency_pause_enabled", scheduling.error_codes)
        self.assertIn("emergency_pause_enabled", publishing.error_codes)

    def test_missing_required_media_blocks_media_required_platform(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(db_path, platform="instagram", media_ids=[])
        service.approve(draft.id, actor=Actor(actorType="user"))

        result = service.check_scheduling_eligibility(draft.id)

        self.assertFalse(result.eligible)
        self.assertIn("missing_required_media", result.error_codes)

    def test_publishing_requires_connected_account_when_social_account_model_exists(self):
        db_path = self._database()
        service = ApprovalQueueService(db_path)
        draft = self._saved_draft(db_path)
        service.approve(draft.id, actor=Actor(actorType="user"))

        result = service.check_publishing_eligibility(draft.id)

        self.assertFalse(result.eligible)
        self.assertIn("missing_connected_account", result.error_codes)
        self.assertIn("real_publishing_disabled_by_policy", result.warning_codes)


if __name__ == "__main__":
    unittest.main()
